"""
The script base class and the bar loop.

A converted script subclasses ``Script``: declaration as class attributes, ``init()`` for
inputs and ``var`` state, ``on_bar()`` for the per-bar body. ``run()`` executes it over a
DataFrame of bars and returns plots, signals and — for strategies — the broker's trades,
equity curves and metrics.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
import pandas as pd

from . import core
from .broker import LONG, SHORT, Broker, StrategyConfig
from .core import NA, Context, DerivedSeries, Hist, PriceSeries, RT, callsite, fl, register_stop
from .symbols import SymbolInfo

# ─────────────────────────────────────────────────────────────── timeframes
def tf_seconds(tf: str) -> int:
    """TradingView timeframe string → seconds ("1", "60", "240", "D", "3D", "W", "M", "1S")."""
    t = str(tf).strip().upper()
    if t.endswith("S") and t[:-1].isdigit():
        return int(t[:-1])
    if t.isdigit():
        return int(t) * 60
    num = "".join(ch for ch in t if ch.isdigit()) or "1"
    unit = "".join(ch for ch in t if ch.isalpha())
    mult = int(num)
    return mult * {"D": 86400, "W": 7 * 86400, "M": 30 * 86400, "H": 3600}[unit]


def tf_is_intraday(tf: str) -> bool:
    return tf_seconds(tf) < 86400


# ─────────────────────────────────────────────────────────────── inputs
class Inputs:
    """``input.*``: returns the override for this backtest, else the default; records the
    definitions so a backtest can list its parameters."""

    def __init__(self, script: "Script", overrides: dict | None) -> None:
        self._s = script
        self.overrides = dict(overrides or {})
        self.defs: list[dict] = []

    def _get(self, kind: str, defval: Any, title: str | None, **meta: Any) -> Any:
        key = title or f"input {len(self.defs) + 1}"
        self.defs.append({"kind": kind, "title": key, "default": _jsonable(defval), **meta})
        return self.overrides.get(key, defval)

    def __call__(self, defval: Any, title: str | None = None, **kw: Any) -> Any:
        if isinstance(defval, PriceSeries):
            return self.source(defval, title, **kw)
        kind = "bool" if isinstance(defval, bool) else "int" if isinstance(defval, int) else \
            "float" if isinstance(defval, float) else "string"
        return self._get(kind, defval, title, **_meta(kw))

    def int(self, defval: int, title: str | None = None, **kw: Any) -> int:
        return int(self._get("int", defval, title, **_meta(kw)))

    def float(self, defval: float, title: str | None = None, **kw: Any) -> float:
        return float(self._get("float", defval, title, **_meta(kw)))

    def bool(self, defval: bool, title: str | None = None, **kw: Any) -> bool:
        return bool(self._get("bool", defval, title, **_meta(kw)))

    def string(self, defval: str, title: str | None = None, **kw: Any) -> str:
        return str(self._get("string", defval, title, **_meta(kw)))

    def text_area(self, defval: str, title: str | None = None, **kw: Any) -> str:
        return str(self._get("text_area", defval, title, **_meta(kw)))

    def timeframe(self, defval: str, title: str | None = None, **kw: Any) -> str:
        v = str(self._get("timeframe", defval, title, **_meta(kw)))
        return v or self._s.timeframe.period          # "" means the chart's timeframe

    def session(self, defval: str, title: str | None = None, **kw: Any) -> str:
        return str(self._get("session", defval, title, **_meta(kw)))

    def symbol(self, defval: str, title: str | None = None, **kw: Any) -> str:
        return str(self._get("symbol", defval, title, **_meta(kw)))

    def color(self, defval: Any, title: str | None = None, **kw: Any) -> Any:
        return self._get("color", defval, title, **_meta(kw))

    def price(self, defval: float, title: str | None = None, **kw: Any) -> float:
        return float(self._get("price", defval, title, **_meta(kw)))

    def time(self, defval: int, title: str | None = None, **kw: Any) -> int:
        return int(self._get("time", defval, title, **_meta(kw)))

    def enum(self, defval: Any, title: str | None = None, **kw: Any) -> Any:
        return self._get("enum", defval, title, **_meta(kw))

    def source(self, defval: Any, title: str | None = None, **kw: Any) -> Any:
        default_name = defval.name if isinstance(defval, PriceSeries) else str(defval)
        name = self._get("source", default_name, title, **_meta(kw))
        return self._s.source_by_name(name)


def _meta(kw: dict) -> dict:
    keep = ("minval", "maxval", "step", "options", "group", "inline", "tooltip", "confirm", "display")
    return {k: _jsonable(v) for k, v in kw.items() if k in keep}


def _jsonable(v: Any) -> Any:
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, PriceSeries):
        return v.name
    return str(v)


# ─────────────────────────────────────────────────────────────── outputs
@dataclass
class Outputs:
    n: int
    plots: dict[str, np.ndarray] = field(default_factory=dict)
    plot_meta: dict[str, dict] = field(default_factory=dict)
    shapes: dict[str, np.ndarray] = field(default_factory=dict)
    alerts: dict[str, list[int]] = field(default_factory=dict)
    alert_messages: list[tuple[int, str]] = field(default_factory=list)
    bgcolor: list[tuple[int, Any]] = field(default_factory=list)
    _names: dict = field(default_factory=dict)

    def name_for(self, key: tuple, title: str | None, prefix: str) -> str:
        nm = self._names.get(key)
        if nm is None:
            base = title or f"{prefix} {len(self._names) + 1}"
            nm = base
            k = 2
            existing = set(self._names.values())
            while nm in existing:
                nm = f"{base} ({k})"
                k += 1
            self._names[key] = nm
        return nm


# ─────────────────────────────────────────────────────────────── barstate / timeframe
class BarState:
    def __init__(self, ctx: Context) -> None:
        self._c = ctx

    @property
    def isfirst(self) -> bool: return self._c.bar_index == 0
    @property
    def islast(self) -> bool: return self._c.bar_index == self._c.n_bars - 1
    @property
    def isconfirmed(self) -> bool: return True
    @property
    def isnew(self) -> bool: return True
    @property
    def ishistory(self) -> bool: return True
    @property
    def isrealtime(self) -> bool: return False
    @property
    def islastconfirmedhistory(self) -> bool: return self._c.bar_index == self._c.n_bars - 1


class TimeframeInfo:
    def __init__(self, period: str, ctx: Context) -> None:
        self.period = str(period)
        self._c = ctx
        secs = tf_seconds(period)
        self.in_seconds_value = secs
        self.isseconds = secs < 60
        self.isminutes = 60 <= secs < 86400
        self.isintraday = secs < 86400
        self.isdaily = 86400 <= secs < 7 * 86400
        self.isweekly = 7 * 86400 <= secs < 28 * 86400
        self.ismonthly = secs >= 28 * 86400
        self.isdwm = not self.isintraday
        self.multiplier = int("".join(ch for ch in self.period if ch.isdigit()) or "1")

    def in_seconds(self, tf: str | None = None) -> int:
        return tf_seconds(tf) if tf else self.in_seconds_value

    def change(self, tf: str) -> bool:
        """``timeframe.change(tf)``: true on the first bar of a new ``tf`` period."""
        return self._c.period_change(tf)


# ─────────────────────────────────────────────────────────────── the script
class Script:
    """Base class for converted scripts."""

    TITLE = ""
    SHORT_TITLE = ""
    OVERLAY = True
    PINE_VERSION = 5
    STRATEGY: dict | None = None          # strategy() arguments; None → indicator
    SOURCE: dict = {}                     # id, url, author, licence of the Pine original
    MAX_LINES = MAX_BOXES = MAX_LABELS = MAX_POLYLINES = 50   # Pine's max_*_count

    def init(self) -> None:
        pass

    def on_bar(self) -> None:
        raise NotImplementedError

    # ── series, available in init() and on_bar()
    def source_by_name(self, name: str) -> Any:
        name = str(name).lower()
        m = {"open": self.open, "high": self.high, "low": self.low, "close": self.close,
             "volume": self.volume, "hl2": self.hl2, "hlc3": self.hlc3, "ohlc4": self.ohlc4,
             "hlcc4": self.hlcc4, "time": self.time}
        if name not in m:
            raise ValueError(f"unknown source {name!r}")
        return m[name]

    @property
    def bar_index(self) -> int:
        return self._ctx.bar_index

    @property
    def last_bar_index(self) -> int:
        return self._ctx.n_bars - 1

    def H(self, name: str) -> Hist:
        """Script-level variable with history: ``self.H('x').set(v)``; ``self.H('x')[1]``."""
        h = self._ctx.named.get(name)
        if h is None:
            h = Hist()
            self._ctx.named[name] = h
        return h

    # ── time (Pine names; exchange timezone unless tz given)
    def _cal(self, t: Any, tz: str | None):
        if t is None:
            return self._ctx.cal_row(self._ctx.bar_index)
        ts = pd.Timestamp(int(fl(t)), unit="ms", tz="UTC").tz_convert(tz or self.syminfo.timezone)
        return ts

    def year(self, t: Any = None, tz: str | None = None) -> int: return int(self._cal(t, tz).year)
    def month(self, t: Any = None, tz: str | None = None) -> int: return int(self._cal(t, tz).month)
    def dayofmonth(self, t: Any = None, tz: str | None = None) -> int: return int(self._cal(t, tz).day)
    def dayofweek(self, t: Any = None, tz: str | None = None) -> int:
        """Pine numbering: 1 = Sunday … 7 = Saturday."""
        return (int(self._cal(t, tz).dayofweek) + 1) % 7 + 1
    def hour(self, t: Any = None, tz: str | None = None) -> int: return int(self._cal(t, tz).hour)
    def minute(self, t: Any = None, tz: str | None = None) -> int: return int(self._cal(t, tz).minute)
    def second(self, t: Any = None, tz: str | None = None) -> int: return int(self._cal(t, tz).second)
    def weekofyear(self, t: Any = None, tz: str | None = None) -> int: return int(self._cal(t, tz).isocalendar()[1])

    def timestamp(self, *args: Any) -> int:
        """``timestamp(year, month, day, hour, minute, second)`` or with a leading tz string."""
        tz = self.syminfo.timezone
        if args and isinstance(args[0], str):
            tz, args = args[0], args[1:]
        y, mo, d, *rest = args
        h, mi, s = (list(rest) + [0, 0, 0])[:3]
        ts = pd.Timestamp(year=int(y), month=int(mo), day=int(d), hour=int(h), minute=int(mi),
                          second=int(s), tz=tz)
        return int(ts.tz_convert("UTC").value // 1_000_000)

    def time_in_session(self, session: str, tz: str | None = None, t: Any = None) -> bool:
        """``not na(time(timeframe.period, session))`` — bar start inside the session."""
        return self._ctx.in_session(session, tz or self.syminfo.timezone, t)

    def time_fn(self, timeframe: str | None = None, session: str | None = None, tz: str | None = None) -> float:
        """Pine ``time(timeframe, session, tz)``: bar time, or na outside the session."""
        if session and not self.time_in_session(session, tz):
            return NA
        if timeframe and timeframe != self.timeframe.period:
            return float(self._ctx.period_start_time(timeframe))
        return float(self._ctx.time_arr[self._ctx.bar_index])

    # ── outputs
    def plot(self, series: Any, title: str | None = None, color: Any = None, **kw: Any) -> Any:
        c = self._ctx
        key = callsite(1)
        name = self._out.name_for(key, title, "Plot")
        arr = self._out.plots.get(name)
        if arr is None:
            arr = np.full(c.n_bars, np.nan)
            self._out.plots[name] = arr
            self._out.plot_meta[name] = {"color": _jsonable(color), **{k: _jsonable(v) for k, v in kw.items()}}
        arr[c.bar_index] = fl(series) if not isinstance(series, bool) else float(series)
        return name

    def plotshape(self, series: Any, title: str | None = None, **kw: Any) -> None:
        c = self._ctx
        key = callsite(1)
        name = self._out.name_for(key, title, "Shape")
        arr = self._out.shapes.get(name)
        if arr is None:
            arr = np.zeros(c.n_bars, dtype=bool)
            self._out.shapes[name] = arr
        arr[c.bar_index] = core.truthy(series)

    plotchar = plotshape
    plotarrow = plotshape

    def plotcandle(self, *a: Any, **kw: Any) -> None: pass
    def plotbar(self, *a: Any, **kw: Any) -> None: pass
    def hline(self, price: Any, title: str | None = None, **kw: Any) -> float: return fl(price)
    def fill(self, *a: Any, **kw: Any) -> None: pass
    def barcolor(self, *a: Any, **kw: Any) -> None: pass

    def bgcolor(self, color: Any, *a: Any, **kw: Any) -> None:
        if color is not None and not (isinstance(color, float) and math.isnan(color)):
            self._out.bgcolor.append((self._ctx.bar_index, color))

    def alertcondition(self, condition: Any, title: str | None = None, message: str | None = None) -> None:
        key = callsite(1)
        name = self._out.name_for(key, title, "Alert")
        hits = self._out.alerts.setdefault(name, [])
        if core.truthy(condition):
            hits.append(self._ctx.bar_index)

    def alert(self, message: str, freq: Any = None) -> None:
        self._out.alert_messages.append((self._ctx.bar_index, str(message)))

    # ── request.security
    def security(self, symbol: str | None, timeframe: str, fn: Callable[["SeriesView"], Any],
                 lookahead: bool = False, gaps: bool = False) -> Any:
        """``request.security``. ``fn`` receives a SeriesView of the requested bars and
        returns a value (or a tuple). Historical semantics:
          lookahead off — a higher-timeframe value appears on the LAST chart bar of its
          period (earlier bars show the previous period's value): no look-ahead;
          lookahead on  — every chart bar of the period shows the period's final value.
        """
        from .security import security_value
        return security_value(self, callsite(1), symbol, timeframe, fn, lookahead, gaps)

    @property
    def strategy(self) -> "StrategyFacade":
        if self._strategy is None:
            raise RuntimeError("strategy.* used in an indicator (STRATEGY is None)")
        return self._strategy


class SeriesView:
    """The bar series of another symbol/timeframe, for ``request.security`` expressions."""

    def __init__(self, ctx: Context, syminfo: SymbolInfo, period: str) -> None:
        self._ctx = ctx
        self.syminfo = syminfo
        self.open = PriceSeries(ctx.open_arr, "open")
        self.high = PriceSeries(ctx.high_arr, "high")
        self.low = PriceSeries(ctx.low_arr, "low")
        self.close = PriceSeries(ctx.close_arr, "close")
        self.volume = PriceSeries(ctx.volume_arr, "volume")
        self.time = PriceSeries(ctx.time_arr, "time")
        self.hl2 = DerivedSeries(lambda i: (ctx.high_arr[i] + ctx.low_arr[i]) / 2, "hl2")
        self.hlc3 = DerivedSeries(lambda i: (ctx.high_arr[i] + ctx.low_arr[i] + ctx.close_arr[i]) / 3, "hlc3")
        self.ohlc4 = DerivedSeries(lambda i: (ctx.open_arr[i] + ctx.high_arr[i] + ctx.low_arr[i] + ctx.close_arr[i]) / 4, "ohlc4")
        self.hlcc4 = DerivedSeries(lambda i: (ctx.high_arr[i] + ctx.low_arr[i] + 2 * ctx.close_arr[i]) / 4, "hlcc4")
        self.timeframe = TimeframeInfo(period, ctx)

    @property
    def bar_index(self) -> int:
        return self._ctx.bar_index


class StrategyFacade:
    """``strategy.*`` for a running script."""

    long = LONG
    short = SHORT

    def __init__(self, broker: Broker) -> None:
        self._b = broker

    def entry(self, id: str, direction: int, qty: Any = NA, limit: Any = NA, stop: Any = NA, **kw: Any) -> None:
        self._b.entry(id, direction, qty, limit, stop, **kw)

    def order(self, id: str, direction: int, qty: Any = NA, limit: Any = NA, stop: Any = NA, **kw: Any) -> None:
        self._b.order(id, direction, qty, limit, stop, **kw)

    def exit(self, id: str, from_entry: str = "", **kw: Any) -> None:
        self._b.exit(id, from_entry, **kw)

    def close(self, id: str, comment: str = "", **kw: Any) -> None:
        self._b.close(id, comment, **kw)

    def close_all(self, comment: str = "", **kw: Any) -> None:
        self._b.close_all(comment, **kw)

    def cancel(self, id: str) -> None:
        self._b.cancel(id)

    def cancel_all(self) -> None:
        self._b.cancel_all()

    @property
    def position_size(self) -> float: return self._b.position_size
    @property
    def position_avg_price(self) -> float: return self._b.position_avg_price
    @property
    def position_entry_name(self) -> str: return self._b.open[-1].entry_id if self._b.open else ""
    @property
    def opentrades(self) -> int: return len(self._b.open)
    @property
    def closedtrades(self) -> int: return len(self._b.closed)
    @property
    def wintrades(self) -> int: return sum(1 for t in self._b.closed if t.profit > 0)
    @property
    def losstrades(self) -> int: return sum(1 for t in self._b.closed if t.profit < 0)
    @property
    def eventrades(self) -> int: return sum(1 for t in self._b.closed if t.profit == 0)
    @property
    def netprofit(self) -> float: return self._b.netprofit
    @property
    def grossprofit(self) -> float: return self._b.grossprofit
    @property
    def grossloss(self) -> float: return self._b.grossloss
    @property
    def openprofit(self) -> float: return self._b.openprofit()
    @property
    def equity(self) -> float: return self._b.equity()
    @property
    def initial_capital(self) -> float: return self._b.cfg.initial_capital

    # opentrades.* / closedtrades.* accessors (Pine: strategy.opentrades.entry_price(i))
    def opentrades_entry_price(self, i: int) -> float: return self._b.open[int(i)].price
    def opentrades_entry_bar_index(self, i: int) -> int: return self._b.open[int(i)].bar
    def opentrades_entry_time(self, i: int) -> int: return self._b.open[int(i)].time
    def opentrades_entry_id(self, i: int) -> str: return self._b.open[int(i)].entry_id
    def opentrades_size(self, i: int) -> float:
        t = self._b.open[int(i)]
        return t.qty * t.direction
    def closedtrades_entry_price(self, i: int) -> float: return self._b.closed[int(i)].entry_price
    def closedtrades_exit_price(self, i: int) -> float: return self._b.closed[int(i)].exit_price
    def closedtrades_profit(self, i: int) -> float: return self._b.closed[int(i)].profit
    def closedtrades_entry_bar_index(self, i: int) -> int: return self._b.closed[int(i)].entry_bar
    def closedtrades_exit_bar_index(self, i: int) -> int: return self._b.closed[int(i)].exit_bar
    def closedtrades_entry_id(self, i: int) -> str: return self._b.closed[int(i)].entry_id
    def closedtrades_exit_id(self, i: int) -> str: return self._b.closed[int(i)].exit_id
    def closedtrades_size(self, i: int) -> float:
        t = self._b.closed[int(i)]
        return t.qty * t.direction


# ─────────────────────────────────────────────────────────────── running
@dataclass
class RunResult:
    script: Script
    bars: pd.DataFrame
    outputs: Outputs
    inputs: list[dict]
    broker: Broker | None
    symbol: SymbolInfo
    timeframe: str
    drawings: Any = None


@register_stop
def _call_on_bar(script: Script) -> None:
    script.on_bar()


@register_stop
def _call_init(script: Script) -> None:
    script.init()


def run(script_cls: type[Script], bars: pd.DataFrame, *, params: dict | None = None,
        symbol: SymbolInfo | None = None, timeframe: str = "D",
        ltf: list | None = None, data_provider: Callable | None = None,
        strategy_overrides: dict | None = None) -> RunResult:
    """Run ``script_cls`` over ``bars`` (columns time [ms] or DatetimeIndex, open, high,
    low, close, volume). ``ltf`` = per-bar lists of (o, h, l, c) for the bar magnifier.
    ``data_provider(symbol, timeframe)`` returns bars for request.security on other symbols."""
    sym = symbol or SymbolInfo()
    ctx = Context.from_bars(bars, sym, timeframe)
    ctx.data_provider = data_provider
    script = script_cls()
    script._ctx = ctx
    script.syminfo = sym
    script.timeframe = TimeframeInfo(timeframe, ctx)
    script.barstate = BarState(ctx)
    script._out = Outputs(ctx.n_bars)
    script.input = Inputs(script, params)
    from .draw import Drawings
    script.draw = Drawings(script_cls.MAX_LINES, script_cls.MAX_BOXES, script_cls.MAX_LABELS,
                           script_cls.MAX_POLYLINES)
    script.open, script.high, script.low = ctx.open_s, ctx.high_s, ctx.low_s
    script.close, script.volume, script.time = ctx.close_s, ctx.volume_s, ctx.time_s
    script.hl2, script.hlc3, script.ohlc4, script.hlcc4 = ctx.hl2_s, ctx.hlc3_s, ctx.ohlc4_s, ctx.hlcc4_s
    script.na = NA
    broker = None
    script._strategy = None
    prev = RT.ctx
    RT.ctx = ctx
    try:
        ctx.bar_index = 0
        _call_init(script)
        if script_cls.STRATEGY is not None:
            decl = dict(script_cls.STRATEGY)
            decl.update(strategy_overrides or {})
            cfg = StrategyConfig.from_decl(decl, script_cls.PINE_VERSION)
            broker = Broker(cfg, sym, ctx, ltf)
            script._strategy = StrategyFacade(broker)
        for i in range(ctx.n_bars):
            ctx.bar_index = i
            if broker is not None:
                broker.on_bar_open_and_path(i)
            _call_on_bar(script)
            if broker is not None:
                broker.on_bar_close(i)
    finally:
        RT.ctx = prev
    return RunResult(script=script, bars=ctx.bars_df, outputs=script._out, inputs=script.input.defs,
                     broker=broker, symbol=sym, timeframe=timeframe, drawings=script.draw)


# ─────────────────────────────────────────────────────────────── context construction
def _prepare(bars: pd.DataFrame) -> pd.DataFrame:
    df = bars.copy()
    if "time" not in df.columns:
        idx = df.index
        if not isinstance(idx, pd.DatetimeIndex):
            raise ValueError("bars need a 'time' column (ms or s) or a DatetimeIndex")
        if idx.tz is None:
            idx = idx.tz_localize("UTC")
        df["time"] = idx.tz_convert("UTC").as_unit("ms").asi8   # explicit unit: pandas 3 defaults to us
    t = df["time"].astype("int64")
    if t.iloc[0] < 10_000_000_000:          # seconds → ms
        t = t * 1000
    df["time"] = t
    for col in ("open", "high", "low", "close"):
        df[col] = df[col].astype(float)
    df["volume"] = df["volume"].astype(float) if "volume" in df.columns else np.nan
    return df.reset_index(drop=True)


def _from_bars(cls, bars: pd.DataFrame, sym: SymbolInfo, timeframe: str) -> Context:
    df = _prepare(bars)
    c = cls(len(df))
    c.bars_df = df
    c.sym = sym
    c.tf = timeframe
    c.tf_secs = tf_seconds(timeframe)
    c.time_arr = df["time"].tolist()
    c.open_arr = df["open"].tolist()
    c.high_arr = df["high"].tolist()
    c.low_arr = df["low"].tolist()
    c.close_arr = df["close"].tolist()
    c.volume_arr = df["volume"].tolist()
    c.open_s = PriceSeries(c.open_arr, "open")
    c.high_s = PriceSeries(c.high_arr, "high")
    c.low_s = PriceSeries(c.low_arr, "low")
    c.close_s = PriceSeries(c.close_arr, "close")
    c.volume_s = PriceSeries(c.volume_arr, "volume")
    c.time_s = PriceSeries(c.time_arr, "time")
    H, L, C, O = c.high_arr, c.low_arr, c.close_arr, c.open_arr
    c.hl2_s = DerivedSeries(lambda i: (H[i] + L[i]) / 2, "hl2")
    c.hlc3_s = DerivedSeries(lambda i: (H[i] + L[i] + C[i]) / 3, "hlc3")
    c.ohlc4_s = DerivedSeries(lambda i: (O[i] + H[i] + L[i] + C[i]) / 4, "ohlc4")
    c.hlcc4_s = DerivedSeries(lambda i: (H[i] + L[i] + 2 * C[i]) / 4, "hlcc4")
    local = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert(sym.timezone)
    c.local = local
    start = sym.session_start_minutes
    shifted = local - pd.Timedelta(minutes=start)
    c.trading_day = (shifted.dt.year * 1000 + shifted.dt.dayofyear).tolist()
    c.data_provider = None
    c.security_cache = {}
    c.period_cache = {}
    return c


def _cal_row(self: Context, i: int):
    return self.local.iloc[i]


def _new_trading_day(self: Context, i: int) -> bool:
    if self.tf_secs >= 86400:
        return True
    return i == 0 or self.trading_day[i] != self.trading_day[i - 1]


def _period_keys(self: Context, tf: str) -> list:
    """Key of the ``tf`` period each bar belongs to (aligned to the trading session)."""
    keys = self.period_cache.get(tf)
    if keys is not None:
        return keys
    secs = tf_seconds(tf)
    t = tf.strip().upper()
    td = self.trading_day
    if secs < 86400:
        start = self.sym.session_start_minutes
        loc = self.local
        mins = ((loc.dt.hour * 60 + loc.dt.minute - start) % 1440).tolist()
        per = secs // 60
        keys = [(td[i], mins[i] // per) for i in range(self.n_bars)]
    elif t.endswith("W"):
        shifted = self.local - pd.Timedelta(minutes=self.sym.session_start_minutes)
        iso = shifted.dt.isocalendar()
        mult = tf_seconds(tf) // (7 * 86400)
        keys = [(int(y), int(w) // mult) for y, w in zip(iso["year"], iso["week"])]
    elif t.endswith("M"):
        shifted = self.local - pd.Timedelta(minutes=self.sym.session_start_minutes)
        mult = max(1, tf_seconds(tf) // (30 * 86400))
        keys = [(int(y), (int(m) - 1) // mult) for y, m in zip(shifted.dt.year, shifted.dt.month)]
    else:
        mult = secs // 86400
        uniq = {d: k for k, d in enumerate(dict.fromkeys(td))}
        keys = [uniq[d] // mult for d in td]
    self.period_cache[tf] = keys
    return keys


def _period_change(self: Context, tf: str) -> bool:
    i = self.bar_index
    k = _period_keys(self, tf)
    return i == 0 or k[i] != k[i - 1]


def _period_start_time(self: Context, tf: str) -> int:
    i = self.bar_index
    k = _period_keys(self, tf)
    j = i
    while j > 0 and k[j - 1] == k[i]:
        j -= 1
    return self.time_arr[j]


def _in_session(self: Context, session: str, tz: str, t: Any = None) -> bool:
    if t is None:
        loc = self.local.iloc[self.bar_index]
        loc = loc.tz_convert(tz) if str(loc.tz) != tz else loc
    else:
        loc = pd.Timestamp(int(fl(t)), unit="ms", tz="UTC").tz_convert(tz)
    spec, _, days = session.partition(":")
    if days:
        pine_dow = (loc.dayofweek + 1) % 7 + 1
        if str(pine_dow) not in days:
            return False
    if spec in ("", "0000-0000", "24x7"):
        return True
    a, b = spec.split("-")
    m = loc.hour * 60 + loc.minute
    sa = int(a[:2]) * 60 + int(a[2:4])
    sb = int(b[:2]) * 60 + int(b[2:4])
    return (sa <= m < sb) if sa < sb else (m >= sa or m < sb)


Context.from_bars = classmethod(_from_bars)
Context.cal_row = _cal_row
Context.new_trading_day = _new_trading_day
Context.period_change = _period_change
Context.period_start_time = _period_start_time
Context.in_session = _in_session
