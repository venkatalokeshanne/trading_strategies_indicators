"""Independent check — Super-trend Signal Engine (9VZKhSFJ): daily bars from 2015 (From Year passed as 2015 so the window covers the data). Hand-written SuperTrend on hl2 with ATR10 x 3 (bands stick via nz(prev, current); flip on a
close beyond the previous bar's band); a flip to up buys, to down sells short (reversing, 1 contract). Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "9VZKhSFJ"


def nmax(a, b):
    return np.nan if (np.isnan(a) or np.isnan(b)) else max(a, b)


def nmin(a, b):
    return np.nan if (np.isnan(a) or np.isnan(b)) else min(a, b)


def check():
    df = bars(8000, seed=310)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr = np_atr(h, l, c, 10)
    hl2 = (h + l) / 2
    up_p = dn_p = np.nan
    tr_p = None
    buy, sell = np.zeros(n, bool), np.zeros(n, bool)
    for i in range(n):
        up = hl2[i] - 3.0 * atr[i]
        up1 = up if np.isnan(up_p) else up_p
        c1 = c[i - 1] if i else np.nan
        if c1 > up1:
            up = nmax(up, up1)
        dn = hl2[i] + 3.0 * atr[i]
        dn1 = dn if np.isnan(dn_p) else dn_p
        if c1 < dn1:
            dn = nmin(dn, dn1)
        trend = 1 if tr_p is None else tr_p
        if trend == -1 and c[i] > dn1:
            trend = 1
        elif trend == 1 and c[i] < up1:
            trend = -1
        buy[i] = trend == 1 and tr_p == -1
        sell[i] = trend == -1 and tr_p == 1
        up_p, dn_p, tr_p = up, dn, trend
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if buy[i] else []) + ([("entry", -1)] if sell[i] else []))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"From Year": 2015, "From Month": 1},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
