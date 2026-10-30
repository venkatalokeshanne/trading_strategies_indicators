"""Independent check — 3D EMA (6y8ZLnNi; y5ycp2ed is the same script): daily bars, margin off, 76-tick-per-unit scaling avoided by checking the trail rule directly. EMA7 crossing EMA24 flips the position at the next open (long on over, short on under). While a position exists (as of a bar's close) a trailing stop of 7.6% of that bar's close, expressed in ticks of 0.01 with offset 0,
is issued for the same-direction trade; it works from the next bar."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "6y8ZLnNi"


def check():
    df = bars(9000, seed=470)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    f, s = np_ema(c, 7), np_ema(c, 24)
    up, dn = np_cross_over(f, s), np_cross_under(f, s)
    poscl = np.zeros(n)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if up[i]:
            out.append(("entry", 1))
        if dn[i]:
            out.append(("entry", -1))
        return out

    def trail(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0:
            return None
        return (c[i - 1] * 0.076 / 0.01, 0)

    ref = simulate(o, h, l, c, orders, trail=trail, tick=0.01)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
