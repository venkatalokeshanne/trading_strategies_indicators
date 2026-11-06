"""Independent check — EMA + ADX CLEAN (ALiYX5Gu): hourly bars. EMA10 crossing EMA21 with the full EMA 10/21/55/200 stack and
ADX(14) > 25 opens a trade; any EMA10/21 cross (unfiltered) closes the opposite side. Orders in source order: entries, then closes."""
import numpy as np

from indep import bars, compare, np_adx, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "ALiYX5Gu"


def check():
    df = bars(20000, seed=96, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    e10, e21, e55, e200 = (np_ema(c, n) for n in (10, 21, 55, 200))
    adx = np_adx(h, l, c, 14)
    up, dn = np_cross_over(e10, e21), np_cross_under(e10, e21)
    with np.errstate(invalid="ignore"):
        lg = up & (e10 > e21) & (e21 > e55) & (e55 > e200) & (adx > 25)
        sg = dn & (e10 < e21) & (e21 < e55) & (e55 < e200) & (adx > 25)

    def orders(i, pos):
        out = []
        if lg[i]:
            out.append(("entry", 1))
        if sg[i]:
            out.append(("entry", -1))
        if dn[i]:
            out.append(("close", 1))
        if up[i]:
            out.append(("close", -1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
