"""Independent check — ATR Trailing Stop + EMA Filter (43eIQfDj): hourly bars. ATR(14)*2 trailing line that flips on a close through it; a flip to up while the close is above EMA200
goes long, a flip to down below EMA200 goes short (reversing, no brackets). The line is (re)initialised to close - 2 ATR while it is na (ATR not ready); upTrend[1] is the previous bar's
final value (na = false). Plain loop with Pine's na handling (math.max/min are na if either side is)."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "43eIQfDj"


def nmax(a, b):
    return np.nan if (np.isnan(a) or np.isnan(b)) else max(a, b)


def nmin(a, b):
    return np.nan if (np.isnan(a) or np.isnan(b)) else min(a, b)


def check():
    df = bars(20000, seed=184, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr, e = np_atr(h, l, c, 14), np_ema(c, 200)
    trail, up = np.nan, True
    prev_up = False                                   # upTrend[1] on bar 0 is na = false
    fl, fs = np.zeros(n, bool), np.zeros(n, bool)
    for i in range(n):
        ls, ss = c[i] - atr[i] * 2.0, c[i] + atr[i] * 2.0
        pu = prev_up
        if np.isnan(trail):
            trail, up = ls, True
        else:
            if pu:
                trail = ss if c[i] < trail else nmax(trail, ls)
            else:
                trail = ls if c[i] > trail else nmin(trail, ss)
            up = bool(c[i] >= trail)
        fl[i] = up and not pu and c[i] > e[i]
        fs[i] = (not up) and pu and c[i] < e[i]
        prev_up = up
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if fl[i] and pos <= 0 else []) + ([("entry", -1)] if fs[i] and pos >= 0 else []))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
