"""Independent check — 55/20 Wilder's MACD Trend (AR7LCcVC): RMA 20/55 cross, stop-and-reverse."""
from indep import bars, compare, np_cross_over, np_cross_under, np_rma, run_conversion, simulate


def check():
    df = bars(3000, seed=26)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    f, s = np_rma(c, 20), np_rma(c, 55)
    up, dn = np_cross_over(f, s), np_cross_under(f, s)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if up[i] else []) + ([("entry", -1)] if dn[i] else []))
    return compare(run_conversion("AR7LCcVC", df), ref)
