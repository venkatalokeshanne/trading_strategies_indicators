"""Independent check — FVG Short (Kw11wQxH): short when high[2] < low on a red bar with ATR >= 2,
only while flat; the bracket is re-placed each bar while short, so on bar i it uses ATR[i-1]."""
import numpy as np

from indep import bars, compare, np_atr, run_conversion, simulate

TV_ID = "Kw11wQxH"


def check():
    df = bars(3000, seed=73)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    atr = np_atr(h, l, c, 14)
    tgt = np.floor(atr / 0.5) * 0.5
    sig = np.r_[False, False, h[:-2] < l[2:]] & (c < o) & (atr >= 2)
    ref = simulate(o, h, l, c, lambda i, pos: [("entry", -1)] if sig[i] and pos == 0 else [],
                   stop=lambda i, pos, ep, eb: None if i == eb else ep + 1.5 * tgt[i - 1],
                   target=lambda i, pos, ep, eb: None if i == eb else ep - tgt[i - 1])
    return compare(run_conversion(TV_ID, df), ref)
