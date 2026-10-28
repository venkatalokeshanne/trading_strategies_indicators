"""Independent check — Micro-Trendline Momentum Breakout (4NV68grw): daily bars. Pivot highs / lows (3 bars left, 1 right, strict on continuous prices) confirmed one bar later give var (value, bar index) pairs; the last two
define a line value_1 + slope * (bar - idx_1). Close crossing over the resistance line with close > HMA20 and RSI14 < 70 goes long when flat (under the support line, below HMA20, RSI > 30 short). Entry + exit are issued on the
signal bar (stop = close -/+ 1.5 ATR14, limit = 2 R), so the bracket works from the fill bar."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_rsi, np_wma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "4NV68grw"


def check():
    df = bars(8000, seed=219)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    hma = np_wma(2 * np_wma(c, 10) - np_wma(c, 20), 4)
    rsi, atr = np_rsi(c, 14), np_atr(h, l, c, 14)
    res, sup = np.full(n, np.nan), np.full(n, np.nan)
    hi = [None, None]                                    # [(value, idx) latest, previous]
    lo = [None, None]
    for i in range(n):
        if i >= 4:
            if h[i - 1] > h[i - 4:i - 1].max() and h[i - 1] > h[i]:
                hi = [(h[i - 1], i - 1), hi[0]]
            if l[i - 1] < l[i - 4:i - 1].min() and l[i - 1] < l[i]:
                lo = [(l[i - 1], i - 1), lo[0]]
        if hi[0] and hi[1]:
            (v1, i1), (v2, i2) = hi
            res[i] = v1 + (v1 - v2) / (i1 - i2) * (i - i1)
        if lo[0] and lo[1]:
            (v1, i1), (v2, i2) = lo
            sup[i] = v1 + (v1 - v2) / (i1 - i2) * (i - i1)
    with np.errstate(invalid="ignore"):
        lg = np_cross_over(c, res) & (c > hma) & (rsi < 70)
        sg = np_cross_under(c, sup) & (c < hma) & (rsi > 30)
    lvl = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}

    def orders(i, pos):
        out = []
        if lg[i] and pos == 0:
            sl = c[i] - atr[i] * 1.5
            out.append(("entry", 1)); lvl[1] = (sl, c[i] + (c[i] - sl) * 2.0)
        if sg[i] and pos == 0:
            sl = c[i] + atr[i] * 1.5
            out.append(("entry", -1)); lvl[-1] = (sl, c[i] - (sl - c[i]) * 2.0)
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: lvl[pos][0], target=lambda i, pos, ep, eb: lvl[pos][1])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
