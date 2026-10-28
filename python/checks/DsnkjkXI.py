"""Independent check — EMA Stack Strategy (DsnkjkXI): daily bars, slippage 0, orders at the signal close (process_orders_on_close), all six EMAs (5/20/50/90/140/200) in the bias. Bull bias = each EMA above the next slower one; fullBull = bull bias and EMA5 > EMA20; signal = fullBull and (EMA5 crossing over EMA20 or the bias is newly true).
Long when not long (the short is closed first), short mirrored; EMA5 crossing under EMA20 closes a long (over closes a short) unless the opposite entry fires on that bar."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "DsnkjkXI"


def check():
    df = bars(9000, seed=39)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    e = [np_ema(c, k) for k in (5, 20, 50, 90, 140, 200)]
    with np.errstate(invalid="ignore"):
        bull = np.ones(n, bool)
        bear = np.ones(n, bool)
        for k in range(5):
            bull &= e[k] > e[k + 1]
            bear &= e[k] < e[k + 1]
        nb = bull & ~np.r_[False, bull[:-1]]
        ns = bear & ~np.r_[False, bear[:-1]]
        up, dn = np_cross_over(e[0], e[1]), np_cross_under(e[0], e[1])
        ls = bull & (e[0] > e[1]) & (up | nb)
        ss = bear & (e[0] < e[1]) & (dn | ns)

    def orders(i, pos):
        out = []
        if ls[i] and pos <= 0:
            out += [("close", -1), ("entry", 1)]
        if ss[i] and pos >= 0:
            out += [("close", 1), ("entry", -1)]
        if pos > 0 and dn[i] and not ss[i]:
            out.append(("close", 1))
        if pos < 0 and up[i] and not ls[i]:
            out.append(("close", -1))
        return out

    ref = simulate(o, h, l, c, orders, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
