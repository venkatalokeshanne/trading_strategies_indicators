"""Day-trade adapter around pinelib: gate entries, flatten at EOD, map costs, extract per-day trades."""
import hashlib
import importlib.util
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from src import config
from src.data.quality import load
from src.data.twelvedata import TZ

COLS = ["day", "entry_time", "exit_time", "dir", "qty", "entry_price", "exit_price", "pnl", "commission"]


def gate_minutes(gate: str) -> int:
    """'open' -> 570 (09:30 ET), 'open+10' -> 580."""
    return 570 + (int(gate.split("+")[1]) if "+" in gate else 0)


def load_script(path):
    config.setup_pinelib()
    from pinelib import Script
    spec = importlib.util.spec_from_file_location("strat_" + hashlib.md5(str(path).encode()).hexdigest()[:8], path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return next(c for c in vars(m).values() if isinstance(c, type) and issubclass(c, Script) and c is not Script
                and c.__module__ == m.__name__)


def resample(bars1m: pd.DataFrame, tf: int) -> pd.DataFrame:
    """RTH 1-min -> tf-minute bars aligned to 09:30 ET; columns time[ms UTC], OHLCV."""
    d = bars1m.set_index(bars1m["time"].dt.tz_convert(TZ))
    r = d.resample(f"{tf}min", origin="start_day", offset="9h30min", label="left", closed="left").agg(
        dict(open="first", high="max", low="min", close="last", volume="sum")).dropna(subset=["open"])
    r.insert(0, "time", r.index.tz_convert("UTC").as_unit("ms").asi8)
    return r.reset_index(drop=True)


class _Gated:
    """strategy.* proxy: blocks entries outside [gate, last-bar) and past max entries/day."""

    def __init__(self, real, owner):
        self._r, self._o = real, owner

    def __getattr__(self, k):
        return getattr(self._r, k)

    def _allowed(self) -> bool:
        o, i = self._o, self._o._ctx.bar_index
        if not (o._gate_ok[i] and i < o._penult[i]):
            return False
        b = self._r._b
        n = sum(1 for t in b.closed if t.entry_bar >= o._day_start[i]) + sum(1 for t in b.open if t.bar >= o._day_start[i])
        return n < o._max_entries

    def entry(self, *a, **k):
        if self._allowed():
            self._r.entry(*a, **k)

    def order(self, *a, **k):
        if self._allowed():
            self._r.order(*a, **k)


def make_day_script(cls, bars: pd.DataFrame, tf: int, gate: str, max_entries: int):
    """Subclass of the strategy with the gate/EOD/entry-cap logic; per-bar tables are precomputed."""
    et = pd.to_datetime(bars["time"], unit="ms", utc=True).dt.tz_convert(TZ)
    day = et.dt.date.values
    mins = (et.dt.hour * 60 + et.dt.minute).values
    n = len(bars)
    day_start, penult = np.zeros(n, int), np.zeros(n, int)
    for d in pd.unique(day):
        idx = np.flatnonzero(day == d)
        day_start[idx] = idx[0]
        penult[idx] = idx[-1] - 1          # close_all here fills at the open of the day's last bar
    gate_ok = (mins + tf) >= gate_minutes(gate)   # decision happens at bar close, so no look before the gate

    class DayScript(cls):
        _gate_ok, _day_start, _penult, _max_entries = gate_ok, day_start, penult, max_entries

        @property
        def strategy(self):
            if not hasattr(self, "_gs"):
                self._gs = _Gated(self._strategy, self)
            return self._gs

        def on_bar(self):
            super().on_bar()
            i = self._ctx.bar_index
            if i == self._penult[i]:
                self._strategy.cancel_all()
                self._strategy.close_all("EOD")

    DayScript.__name__ = cls.__name__
    return DayScript


def cost_overrides(cfg, symbol: str, price: float, mintick: float = 0.01) -> dict:
    c = cfg["costs"][config.tier(cfg, symbol)]
    ticks = max(1, round(c["slippage_bps"] * price / 1e4 / mintick))
    a = cfg["adapter"]
    return dict(commission_type="cash_per_contract", commission_value=c["commission_per_share"],
                slippage=ticks, initial_capital=a["initial_capital"],
                default_qty_type="cash", default_qty_value=a["notional"])


def run_day_trades(cfg, script_path, symbol: str, tf: int, gate: str, start: str, end: str,
                   params: dict | None = None, bars1m: pd.DataFrame | None = None) -> pd.DataFrame:
    config.setup_pinelib()
    from pinelib.runner import run
    from pinelib.symbols import SymbolInfo
    if bars1m is None:
        bars1m = load(cfg, symbol)
    lo = pd.Timestamp(start, tz=TZ) - pd.Timedelta(days=cfg["adapter"]["warmup_days"])
    hi = pd.Timestamp(end, tz=TZ) + pd.Timedelta(days=1)
    b1 = bars1m[(bars1m["time"] >= lo) & (bars1m["time"] < hi)]
    if b1.empty:                                   # symbol has no bars in the window
        return pd.DataFrame(columns=COLS)
    bars = resample(b1, tf)
    cls = make_day_script(script_path if isinstance(script_path, type) else load_script(script_path), bars, tf, gate, cfg["max_entries_per_day"])
    r = run(cls, bars, params=params, symbol=SymbolInfo(tickerid=f"NASDAQ:{symbol}", timezone=TZ),
            timeframe=str(tf), strategy_overrides=cost_overrides(cfg, symbol, float(b1["close"].median())))
    t = pd.DataFrame([dict(entry_time=pd.Timestamp(x.entry_time, unit="ms", tz="UTC").tz_convert(TZ),
                           exit_time=pd.Timestamp(x.exit_time, unit="ms", tz="UTC").tz_convert(TZ),
                           dir=x.direction, qty=x.qty, entry_price=x.entry_price, exit_price=x.exit_price,
                           pnl=x.profit, commission=x.commission) for x in r.broker.closed])
    if t.empty:
        return pd.DataFrame(columns=COLS)
    t.insert(0, "day", t["entry_time"].dt.date)
    return t[(t["day"] >= pd.Timestamp(start).date()) & (t["day"] <= pd.Timestamp(end).date())].reset_index(drop=True)[COLS]


def data_hash(bars1m) -> str:
    return str(int(pd.util.hash_pandas_object(bars1m[["time", "close", "volume"]], index=False).sum()))


def cache_key(cfg, script_path, symbol, tf, gate, start, end, params, bars1m, dh: str | None = None) -> str:
    h = hashlib.sha1()
    h.update(Path(script_path).read_bytes())
    h.update(json.dumps([params, symbol, tf, gate, start, end, cfg["costs"], cfg["adapter"],
                         cfg["max_entries_per_day"], cfg["tiers"].get(config.tier(cfg, symbol))], sort_keys=True,
                        default=str).encode())
    h.update((dh or data_hash(bars1m)).encode())
    return h.hexdigest()[:20]


def run_cached(cfg, script_path, symbol, tf, gate, start, end, params=None) -> tuple[pd.DataFrame, bool]:
    """Returns (trades, from_cache)."""
    bars1m = load(cfg, symbol)
    f = cfg["paths"]["db"].parent / "results" / (cache_key(cfg, script_path, symbol, tf, gate, start, end, params, bars1m) + ".parquet")
    if f.exists():
        return pd.read_parquet(f), True
    t = run_day_trades(cfg, script_path, symbol, tf, gate, start, end, params, bars1m)
    f.parent.mkdir(parents=True, exist_ok=True)
    t.to_parquet(f)
    return t, False


def _job(args):
    cfg, *a = args
    return a, *run_cached(cfg, *a)


def run_many(cfg, scripts, symbols, tfs, gates, start, end, workers: int | None = None) -> list[tuple]:
    """All combinations in parallel; returns [(job_args, trades, from_cache)]."""
    jobs = [(cfg, s, y, tf, g, start, end) for s in scripts for y in symbols for tf in tfs for g in gates]
    with ProcessPoolExecutor(workers) as ex:
        return list(ex.map(_job, jobs))
