"""Independent check — MNQ Liquidity Sweep (cnydr3fS), from the Pine source."""
import numpy as np
import pandas as pd
from indep import bars, compare, run_conversion, simulate


def check():
    df = bars(3000, seed=22)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    hh, ll = pd.Series(h).rolling(20).max().to_numpy(), pd.Series(l).rolling(20).min().to_numpy()
    sc = np.r_[False, (h[1:] > hh[:-1]) & (c[1:] < l[:-1])]
    lc = np.r_[False, (l[1:] < ll[:-1]) & (c[1:] > h[:-1])]
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if lc[i] else []) + ([("entry", -1)] if sc[i] else []))
    return compare(run_conversion("cnydr3fS", df), ref)
