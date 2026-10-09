"""Independent check — BB Mean Reversion Long + SL (z1xM8YnZ): up to 3 stacked longs, all
closed together by the single "Exit Long" whose stop/target are reset on every signal.
Own pyramiding loop (indep.simulate is one-position only)."""
import numpy as np

from indep import bars, bracket_hit, compare, np_cross_under, np_sma, run_conversion

TV_ID = "z1xM8YnZ"


def check():
    df = bars(3000, seed=37)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    mid = np_sma(c, 20)
    dev = np.array([np.nan if i < 19 else c[i - 19:i + 1].std() for i in range(len(c))])
    sig = np_cross_under(c, mid - 2.0 * dev)
    ref, open_, sl, tp, pending = [], [], np.nan, np.nan, False
    for i in range(len(c)):
        if pending and len(open_) < 3:
            open_.append((i, o[i]))
        pending = False
        if open_:
            hit = bracket_hit(o[i], h[i], l[i], c[i], 1, sl, tp)
            if hit is not None:
                ref += [(1, eb, ep, i, hit) for eb, ep in open_]
                open_ = []
        if sig[i]:
            pending, sl, tp = True, c[i] * (1 - 1.5 / 100), mid[i]
    return compare(run_conversion(TV_ID, df), ref)
