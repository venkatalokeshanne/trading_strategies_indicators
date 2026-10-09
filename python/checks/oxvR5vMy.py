"""Independent check — Grid Like Strategy (oxvR5vMy): baseline jumps to the close when it moves
more than `point`; fills at the close; bracket = new baseline ± point, working from the next
bar. Martingale quantity is not compared (trade prices/bars only)."""
import numpy as np

from indep import bars, compare, run_conversion, simulate

TV_ID = "oxvR5vMy"


def check():
    df = bars(3000, seed=53)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    pt = 2.0
    b = np.empty(len(c))
    for i in range(len(c)):
        bp = b[i - 1] if i else np.nan
        b[i] = c[i] if np.isnan(bp) or c[i] > bp + pt or c[i] < bp - pt else bp
    bp = np.r_[np.nan, b[:-1]]
    up, dn = b > bp, b < bp
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if up[i] else []) + ([("entry", -1)] if dn[i] else []),
                   stop=lambda i, pos, ep, eb: b[eb] - pos * pt,
                   target=lambda i, pos, ep, eb: b[eb] + pos * pt, on_close=True)
    return compare(run_conversion(TV_ID, df), ref)
