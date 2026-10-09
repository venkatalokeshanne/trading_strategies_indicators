"""Independent check — NIFTY Supertrend CE (9EfIsXWW): long on a Supertrend flip up, close on a
flip down; -15 % / +30 % bracket from the average price, placed from the bar after the fill."""
from indep import bars, compare, np_supertrend, run_conversion, simulate

TV_ID = "9EfIsXWW"


def check():
    df = bars(3000, seed=71)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    _, d = np_supertrend(h, l, c, 3.0, 10)
    buy = [i > 0 and d[i] < 0 and d[i - 1] > 0 for i in range(len(c))]
    ex = [i > 0 and d[i] > 0 and d[i - 1] < 0 for i in range(len(c))]
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if buy[i] else []) + ([("close", 1)] if ex[i] else []),
                   stop=lambda i, pos, ep, eb: None if i == eb else ep * 0.85,
                   target=lambda i, pos, ep, eb: None if i == eb else ep * 1.30)
    return compare(run_conversion(TV_ID, df), ref)
