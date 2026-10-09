"""Independent check — Grover Llorens Activator (VuYM89Tw): plain loop over the recursive
trailing level ts; stop-and-reverse on diff crossing zero."""
import numpy as np

from indep import bars, compare, np_atr, run_conversion, simulate

TV_ID = "VuYM89Tw"


def check():
    df = bars(3000, seed=43)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n, mult = 480, 14
    atr = np_atr(h, l, c, n)
    ts = np.full(len(c), np.nan)
    diff = np.full(len(c), np.nan)
    up, dn = np.zeros(len(c), bool), np.zeros(len(c), bool)
    val, last = np.nan, None
    for i in range(len(c)):
        tp = ts[i - 1] if i else np.nan
        base = tp if not np.isnan(tp) else (c[i - 1] if i else np.nan)
        diff[i] = c[i] - base
        if i:
            up[i] = diff[i] > 0 and diff[i - 1] <= 0
            dn[i] = diff[i] < 0 and diff[i - 1] >= 0
        prev_ts = tp if not np.isnan(tp) else c[i]
        if up[i] or dn[i]:
            val, last = atr[i] / n, i
        bs = np.nan if last is None else i - last
        if up[i]:
            ts[i] = prev_ts - atr[i] * mult
        elif dn[i]:
            ts[i] = prev_ts + atr[i] * mult
        else:
            ts[i] = prev_ts + np.sign(diff[i]) * val * bs
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if up[i] else []) + ([("entry", -1)] if dn[i] else []))
    return compare(run_conversion(TV_ID, df), ref)
