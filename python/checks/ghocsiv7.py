"""Independent check — Gap Filling Strategy (ghocsiv7) on hourly bars: on the first bar of a UTC
day, close everything and fade an opening gap; limit exit at the gap's fill level."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion, simulate

TV_ID = "ghocsiv7"


def check():
    df = bars(24000, seed=79, freq="h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    day = pd.to_datetime(df.time, unit="ms", utc=True).dt.floor("D").to_numpy()
    n = len(c)
    ses = np.r_[False, day[1:] != day[:-1]]
    up, dn, lim = np.zeros(n, bool), np.zeros(n, bool), np.full(n, np.nan)
    for i in range(1, n):
        up[i] = o[i] > h[i - 1] and min(c[i], o[i]) > max(c[i - 1], o[i - 1])
        dn[i] = o[i] < l[i - 1] and min(c[i - 1], o[i - 1]) > max(c[i], o[i])
        val = max(c[i - 1], o[i - 1]) if up[i] else min(c[i - 1], o[i - 1])
        lim[i] = val if ses[i] and (up[i] or dn[i]) else lim[i - 1]

    def orders(i, pos):
        out = [("close", 1), ("close", -1)] if ses[i] else []
        if ses[i] and dn[i]:
            out.append(("entry", 1))
        if ses[i] and up[i]:
            out.append(("entry", -1))
        return out

    ref = simulate(o, h, l, c, orders, target=lambda i, pos, ep, eb: lim[i - 1])
    return compare(run_conversion(TV_ID, df, tf="60"), ref)
