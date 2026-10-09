"""Independent check — EMA 5/13 (N18VdyZl): close the opposite side, then enter."""
from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate


def check():
    df = bars(3000, seed=27)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    f, s = np_ema(c, 5), np_ema(c, 13)
    up, dn = np_cross_over(f, s), np_cross_under(f, s)

    def orders(i, pos):
        out = []
        if up[i]:
            out += [("close", -1), ("entry", 1)]
        if dn[i]:
            out += [("close", 1), ("entry", -1)]
        return out
    return compare(run_conversion("N18VdyZl", df), simulate(o, h, l, c, orders))
