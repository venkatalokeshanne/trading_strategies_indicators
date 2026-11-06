"""Independent check — SMA10 Cross Up +15 pkt (EEF1C7ly): 5-min bars, long only, no brackets. A close crossing over SMA10 arms `watching`; a cross
under disarms it; when armed and the close is >= 15 points above the SMA while flat, buy (disarm); close the long once the close is >= 12 points below
the SMA. Slippage (2 ticks in the original) is 0 on both sides: indep.simulate models slippage on market fills only (checked separately, T04)."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "EEF1C7ly"


def check():
    df = bars(20000, seed=125, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    s = np_sma(c, 10)
    up, dn = np_cross_over(c, s), np_cross_under(c, s)
    watching = [False]

    def orders(i, pos):
        if up[i]:
            watching[0] = True
        if dn[i]:
            watching[0] = False
        out = []
        buy = watching[0] and (c[i] - s[i]) >= 15.0 and pos == 0
        sell = (s[i] - c[i]) >= 12.0 and pos > 0
        if buy:
            watching[0] = False
            out.append(("entry", 1))
        if sell:
            out.append(("close", 1))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
