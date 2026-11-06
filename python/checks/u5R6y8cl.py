"""Independent check — Session King ALMA (u5R6y8cl): 15-min continuous bars, slippage 0. ALMA(9, 0.85, 6) over closes (weights exp(-(i-m)^2/(2 s^2)), m = 0.85*8, s = 9/6, i = 0 for the oldest bar). Long when close > ALMA, short when close < ALMA, flat, and the bar start is inside the
London 05:45-09:45 or 12:00-16:00 window (Europe/London clock, on the date the bar has in New York). Both exits are rebuilt every bar from the position average price (3 ATR14 stop, 6 ATR14 target) and work from the next bar for the trade of their own direction."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "u5R6y8cl"


def alma(x, n=9, off=0.85, sg=6.0):
    m, s = off * (n - 1), n / sg
    w = np.exp(-((np.arange(n) - m) ** 2) / (2 * s * s))
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = (x[i - n + 1:i + 1] * w).sum() / w.sum()
    return out


def check():
    df = bars(14000, seed=112, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    t_utc = pd.to_datetime(df["time"], unit="ms", utc=True)
    ny = t_utc.dt.tz_convert("America/New_York")
    cache = {}

    def win(d, hh, mm):
        k = (d, hh, mm)
        if k not in cache:
            cache[k] = pd.Timestamp(year=d.year, month=d.month, day=d.day, hour=hh, minute=mm, tz="Europe/London")
        return cache[k]

    ins = np.zeros(n, bool)
    for i in range(n):
        d, t = ny.iloc[i], t_utc.iloc[i]
        ins[i] = (win(d, 5, 45) <= t < win(d, 9, 45)) or (win(d, 12, 0) <= t < win(d, 16, 0))
    al, atr = alma(c), np_atr(h, l, c, 14)
    tmp, lv = {}, {}

    def orders(i, pos):
        out = []
        with np.errstate(invalid="ignore"):
            if c[i] > al[i] and ins[i] and pos == 0:
                out.append(("entry", 1))
            if c[i] < al[i] and ins[i] and pos == 0:
                out.append(("entry", -1))
        ep = tmp.get(i) if pos != 0 else None
        lv[i] = None if ep is None else (ep, atr[i])
        return out

    def stop(i, pos, ep, eb):
        tmp[i] = ep
        p = lv.get(i - 1) if i > 0 else None
        if p is None:
            return None
        return p[0] - 3 * p[1] if pos > 0 else p[0] + 3 * p[1]

    def target(i, pos, ep, eb):
        p = lv.get(i - 1) if i > 0 else None
        if p is None:
            return None
        return p[0] + 6 * p[1] if pos > 0 else p[0] - 6 * p[1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
