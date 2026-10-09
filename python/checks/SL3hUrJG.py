"""Independent check — Fast Scalper with Stops (SL3hUrJG): EMA 5/13 reversal, 1 % stop from the
signal close (trail_points without trail_offset never trails in Pine)."""
from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate

TV_ID = "SL3hUrJG"


def check():
    df = bars(3000, seed=29)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    f, s = np_ema(c, 5), np_ema(c, 13)
    up, dn = np_cross_over(f, s), np_cross_under(f, s)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if up[i] else []) + ([("entry", -1)] if dn[i] else []),
                   stop=lambda i, pos, ep, eb: c[eb - 1] * (0.99 if pos > 0 else 1.01))
    return compare(run_conversion(TV_ID, df), ref)
