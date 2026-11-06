"""Independent check — EMA Cross Optimized (TpMkahUp): 5-min bars. EMA 9/21 cross opens a reversing trade whose stop is the signal bar's
low (long) / high (short), working from the fill bar; positions also close on an opposite cross or when the slow EMA turns against
them (close() only acts on a trade that is already open)."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "TpMkahUp"


def check():
    df = bars(20000, seed=101, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    f, s = np_ema(c, 9), np_ema(c, 21)
    up, dn = np_cross_over(f, s), np_cross_under(f, s)
    sp = np.r_[np.nan, s[:-1]]
    with np.errstate(invalid="ignore"):
        turn_dn, turn_up = s < sp, s > sp
    stops = {1: [], -1: []}
    cur = {1: np.nan, -1: np.nan}

    def orders(i, pos):
        out = []
        if up[i]:
            out.append(("entry", 1)); cur[1] = l[i]
        if dn[i]:
            out.append(("entry", -1)); cur[-1] = h[i]
        if pos > 0 and (dn[i] or turn_dn[i]):
            out.append(("close", 1))
        if pos < 0 and (up[i] or turn_up[i]):
            out.append(("close", -1))
        stops[1].append(cur[1]); stops[-1].append(cur[-1])
        return out

    ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: stops[pos][i - 1] if i > 0 else None)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
