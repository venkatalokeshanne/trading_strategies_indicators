"""Independent check — UT Bot v2 (lDGmh7ou): daily bars (Start Date passed as 2015-01-01). ATR(10) x 1 trailing stop: follows the source from below when source > stop[1] and source[1] > stop[1] (max with the previous stop), from above when both
below (min), flips to source -/+ stop distance otherwise; na on the first bars. Source crossing over the stop buys, the stop crossing over the source sells short (reversing). Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_atr, np_cross_over, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "lDGmh7ou"


def check():
    df = bars(5000, seed=280)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sl = 1.0 * np_atr(h, l, c, 10)
    tsl = np.full(n, np.nan)
    for i in range(n):
        p, s, s1 = (tsl[i - 1] if i else np.nan), c[i], (c[i - 1] if i else np.nan)
        pn = 0.0 if np.isnan(p) else p
        if s > p and s1 > p:
            tsl[i] = np.nan if np.isnan(sl[i]) else max(pn, s - sl[i])
        elif s < p and s1 < p:
            tsl[i] = np.nan if np.isnan(sl[i]) else min(pn, s + sl[i])
        elif s > p:
            tsl[i] = s - sl[i]
        else:
            tsl[i] = s + sl[i]
    with np.errstate(invalid="ignore"):
        buy, sell = np_cross_over(c, tsl), np_cross_over(tsl, c)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if buy[i] else []) + ([("entry", -1)] if sell[i] else []))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    start = int(__import__("pandas").Timestamp("2015-01-01", tz="UTC").value // 1_000_000)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Start Date": start},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
