"""Independent check — VWAP Mean Reversion, 2-candle rejection (3Q98707C): 5-min bars on a New York clock.
Entries only in the 18:00-02:59 NY window with a flat EMA20; each signal re-issues the bracket
(stop = VWAP -/+ 4 ATR, target = VWAP at the signal bar). A bracket issued at bar j works from bar j+1."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_vwap, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "3Q98707C"


def check():
    df = bars(20000, seed=74, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    vw, atr = np_vwap(df, c), np_atr(h, l, c, 14)
    hr = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York").dt.hour.to_numpy()
    sess = (hr >= 18) | (hr <= 2)
    e20 = np_ema(c, 20)
    slope = np.abs(e20 - np.r_[[np.nan] * 10, e20[:-10]])
    ub, lb = vw + atr * 2.5, vw - atr * 2.5
    ustop, lstop = vw + atr * 4, vw - atr * 4
    pl, ph = np.r_[np.nan, l[:-1]], np.r_[np.nan, h[:-1]]
    plb, pub = np.r_[np.nan, lb[:-1]], np.r_[np.nan, ub[:-1]]
    with np.errstate(invalid="ignore"):
        flat = slope < atr * 0.4
        lsig = ((pl < plb) | (l < lb)) & (c > lb)
        ssig = ((ph > pub) | (h > ub)) & (c < ub)
        lrr = (vw - c) >= (c - lstop) * 1.5
        srr = (c - vw) >= (ustop - c) * 1.5
        lgo, sgo = lsig & lrr & sess & flat, ssig & srr & sess & flat
    # bracket levels as last issued at or before bar j (stop, target) for each direction
    lv = {1: [], -1: []}
    cur = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}
    for j in range(n):
        if lgo[j]:
            cur[1] = (lstop[j], vw[j])
        if sgo[j]:
            cur[-1] = (ustop[j], vw[j])
        lv[1].append(cur[1]); lv[-1].append(cur[-1])

    def level(k):
        return lambda i, pos, ep, eb: lv[pos][i - 1][k] if i > 0 else None

    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if lgo[i] else []) + ([("entry", -1)] if sgo[i] else []),
                   stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
