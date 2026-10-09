"""Independent check — Buy At Open / Sell At Close Every Bar (7qUtuiBt)."""
from indep import bars, compare, run_conversion, simulate


def check():
    df = bars(2000, seed=23)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    ref = simulate(o, h, l, c, lambda i, pos: [("entry", 1)] if pos == 0 else [("close", 1)])
    return compare(run_conversion("7qUtuiBt", df), ref)
