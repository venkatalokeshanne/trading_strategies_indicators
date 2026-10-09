"""Independent check — Simple Long Only Bot (7YZu94L1), from the Pine source."""
from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate


def check():
    df = bars(3000, seed=21)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    e50, e200 = np_ema(c, 50), np_ema(c, 200)
    buy = np_cross_over(c, e50) & (c > e200)
    sell = np_cross_under(c, e50)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if buy[i] else []) + ([("close", 1)] if sell[i] else []))
    return compare(run_conversion("7YZu94L1", df), ref)
