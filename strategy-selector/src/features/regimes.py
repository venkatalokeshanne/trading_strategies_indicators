"""Soft regimes per symbol-day (weights in [0,1], overlapping), from information known at the open: prior days' bars and today's gap.
8 regimes: trend, chop, hivol, lovol, gap_up, gap_down, gap_flat, event. trend/chop and hivol/lovol average the symbol's own score with the market proxy's."""
import numpy as np
import pandas as pd

from src.data import calendar
from src.data.quality import load
from src.features import day as F
from src.features import events

REGIMES = ["trend", "chop", "hivol", "lovol", "gap_up", "gap_down", "gap_flat", "event"]
ER_N = 10          # days for the efficiency ratio (trend vs chop)
VOL_BASE = 60      # days for the median ATR% a day is compared with


def _daily(b: pd.DataFrame) -> pd.DataFrame:
    d = F._prep(b).groupby("day")
    return pd.DataFrame(dict(h=d["h"].max(), l=d["l"].min(), c=d["c"].last()))


def _scores(b: pd.DataFrame) -> pd.DataFrame:
    """trend_s (0..1), vol_s (0..1) per day, computed from days BEFORE it."""
    x = _daily(b)
    ch = x["c"].diff().abs()
    er = (x["c"] - x["c"].shift(ER_N)).abs() / ch.rolling(ER_N).sum()
    atrp = ((x["h"] - x["l"]) / x["c"]).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    ratio = atrp / atrp.rolling(VOL_BASE, min_periods=20).median()
    out = pd.DataFrame(dict(trend_s=((er - 0.2) / 0.3).clip(0, 1), vol_s=((ratio - 0.8) / 0.4).clip(0, 1)))
    return out.shift(1)                                   # day D sees only through D-1


def regimes(cfg, symbols, days: pd.DatetimeIndex) -> pd.DataFrame:
    """Long table symbol, day, REGIMES."""
    mk = next((m for m in F.MARKET if len(load(cfg, m))), None)
    ms = _scores(load(cfg, mk)) if mk else None
    ev = events.market_flags(days)
    rows = []
    for s in symbols:
        b = load(cfg, s)
        if b.empty:
            continue
        sc = _scores(b).reindex(days)
        if ms is not None:
            sc = (sc + ms.reindex(days)) / 2 if s != mk else sc
        gap = F.day_features(b, "premarket")["gap_atr"].reindex(days)
        ex = events.symbol_flags(cfg, s, days)
        r = pd.DataFrame(index=days)
        r["trend"], r["chop"] = sc["trend_s"], 1 - sc["trend_s"]
        r["hivol"], r["lovol"] = sc["vol_s"], 1 - sc["vol_s"]
        r["gap_up"], r["gap_down"] = (gap / 0.5).clip(0, 1), (-gap / 0.5).clip(0, 1)
        r["gap_flat"] = (1 - r[["gap_up", "gap_down"]].max(axis=1)).where(gap.notna())
        r["event"] = pd.concat([ev["fomc"], ev["cpi"], ev["jobs"], ex["earn_reaction"].fillna(0), ex["earn_tonight"].fillna(0)], axis=1).max(axis=1)
        r.insert(0, "symbol", s)
        rows.append(r.rename_axis("day").reset_index())
    return pd.concat(rows, ignore_index=True)


def report(cfg, top: int = 3, gate: str | None = None) -> pd.DataFrame:
    """Per regime: days with weight > .5 and the top variants by weighted mean daily PnL ($ per symbol-day, no-trade days = 0).
    In-sample illustration of regime dependence, NOT a selection result."""
    from src.store import db
    con = db.connect(cfg, read_only=True)
    runs = con.execute("SELECT DISTINCT variant, symbol, gate, d0, d1 FROM runs WHERE status='ok'").df()
    pnl = con.execute("SELECT variant, symbol, gate, date, pnl FROM daily_pnl").df()
    if gate:
        runs, pnl = runs[runs["gate"] == gate], pnl[pnl["gate"] == gate]
    days = pd.DatetimeIndex(calendar.sessions(runs["d0"].min(), runs["d1"].max())["day"])
    rg = regimes(cfg, sorted(runs["symbol"].unique()), days).set_index(["symbol", "day"])
    grid = runs.merge(pd.DataFrame({"day": days}), how="cross")
    grid = grid.merge(pnl.assign(day=pd.to_datetime(pnl["date"])).rename(columns={"pnl": "pnl"})[["variant", "symbol", "gate", "day", "pnl"]],
                      on=["variant", "symbol", "gate", "day"], how="left").fillna({"pnl": 0.0})
    grid = grid.join(rg, on=["symbol", "day"])
    out = []
    for r in REGIMES:
        g = grid.dropna(subset=[r])
        w = g[r]
        base = g.assign(wp=w * g["pnl"], w=w).groupby(["variant", "gate"])[["wp", "w"]].sum()
        m = (base["wp"] / base["w"]).sort_values(ascending=False)
        n_days = int((rg[r] > 0.5).sum())
        row = dict(regime=r, symbol_days=n_days, avg_all=round(float((g["pnl"] * w).sum() / w.sum()), 2))
        for k, (v, x) in enumerate(list(m.items())[:top]):
            row[f"top{k + 1}"] = f"{v[0].split('|')[0]}/{v[0].split('|')[1]}/{v[1]} {x:+.2f}"
        out.append(row)
    return pd.DataFrame(out)
