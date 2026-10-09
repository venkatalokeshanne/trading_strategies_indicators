"""Independent check — Zero Line Momentum (k13xEYxZ): WaveTrend-style CI, EMA200 filter."""
import numpy as np
from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate


def check():
    df = bars(3000, seed=25)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    e200 = np_ema(c, 200)
    esa = np_ema(c, 9)
    d = np_ema(np.abs(c - esa), 9)
    with np.errstate(divide="ignore", invalid="ignore"):
        ci = (c - esa) / (0.015 * d)
    ci[~np.isfinite(ci)] = np.nan
    wt1 = np_ema(ci, 12)
    lc = (c > e200) & np_cross_over(wt1, 0)
    sc = (c < e200) & np_cross_under(wt1, 0)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if lc[i] else []) + ([("entry", -1)] if sc[i] else []))
    return compare(run_conversion("k13xEYxZ", df), ref)
