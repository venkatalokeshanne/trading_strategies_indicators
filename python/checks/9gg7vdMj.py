"""Independent check — Volatility Surge (9gg7vdMj): daily bars, slippage 0. vi = (highest close of 22 - low)/highest*100; upper = SMA20(vi) + 2*stdev20(vi) (population); surge = vi >= upper. A surge on two consecutive bars with a bullish bar after a non-bullish one (or the mirror)
enters long (short) at the next open, reversing; stop = close -/+ 1.5 ATR14 and target = 1.5x that distance, fixed on the signal bar (a repeat signal replaces them)."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "9gg7vdMj"


def check():
    df = bars(9000, seed=31)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    hc = pd.Series(c).rolling(22).max().to_numpy()
    vi = (hc - l) / hc * 100
    up = np_sma(vi, 20) + 2.0 * pd.Series(vi).rolling(20).std(ddof=0).to_numpy()
    with np.errstate(invalid="ignore"):
        hi = vi >= up
    hi1 = np.r_[False, hi[:-1]]
    bull = c > o
    wb = np.r_[False, bull[:-1]]
    atr = np_atr(h, l, c, 14)
    bs = hi1 & hi & bull & ~wb
    ss = hi1 & hi & ~bull & wb
    lvl = {}

    def orders(i, pos):
        out = []
        if bs[i]:
            out.append(("entry", 1))
            lvl[1] = (c[i] - atr[i] * 1.5, c[i] + atr[i] * 1.5 * 1.5)
        if ss[i]:
            out.append(("entry", -1))
            lvl[-1] = (c[i] + atr[i] * 1.5, c[i] - atr[i] * 1.5 * 1.5)
        return out

    def stop(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][0]

    def target(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
