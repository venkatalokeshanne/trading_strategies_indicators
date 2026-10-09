"""Independent check — EMA9 + RSI50 First Break (V1frjvgM), Pine v6, 100 % of equity, margin
100 %: the entry is refused when the fill open is above the signal close (cost > equity)."""
import numpy as np

from indep import bars, compare, np_ema, np_rsi, run_conversion, simulate

TV_ID = "V1frjvgM"


def check():
    df = bars(3000, seed=61)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    e, rsi = np_ema(c, 9), np_rsi(c, 14)
    cond = (c > e) & (rsi > 50)
    first = cond & ~np.r_[False, cond[:-1]]
    ex = c < e
    n = len(c)

    def orders(i, pos):
        out = []
        if first[i] and i + 1 < n and o[i + 1] <= c[i]:
            out.append(("entry", 1))
        if ex[i]:
            out.append(("close", 1))
        return out

    ref = simulate(o, h, l, c, orders)
    return compare(run_conversion(TV_ID, df), ref)
