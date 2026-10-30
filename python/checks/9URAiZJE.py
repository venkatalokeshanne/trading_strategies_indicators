"""Independent check — 50/200 EMA Cross Filtered Long Only (9URAiZJE): daily bars. EMA50 over EMA200 within 70 bars of the cross, separation > 0.35 %
and a non-falling slow EMA (5-bar slope) enters when flat; a bearish cross closes; 10 % hard stop under the average price re-issued each bar
(works from the bar after the fill). Sizing (5x equity) does not change prices and is not compared."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "9URAiZJE"


def check():
    df = bars(8000, seed=136)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    fast, slow = np_ema(c, 50), np_ema(c, 200)
    up, dn = np_cross_over(fast, slow), np_cross_under(fast, slow)
    since = np.full(n, np.nan)
    last = None
    for i in range(n):
        if up[i]:
            last = i
        since[i] = np.nan if last is None else i - last
    slow5 = np.r_[[np.nan] * 5, slow[:-5]]
    with np.errstate(invalid="ignore", divide="ignore"):
        sep = np.abs(fast - slow) / slow * 100
        slope = (slow - slow5) / slow * 100
        go = (since >= 0) & (since <= 70) & (fast > slow) & (sep > 0.35) & (slope >= 0.0)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if go[i] and pos == 0 else []) + ([("close", 1)] if dn[i] and pos > 0 else []),
                   stop=lambda i, pos, ep, eb: ep * 0.9 if i > eb else None)
    sym = SymbolInfo.make("AMEX:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D"), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
