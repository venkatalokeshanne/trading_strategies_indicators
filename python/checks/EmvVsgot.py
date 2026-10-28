"""Independent check — MACD Crossover (EmvVsgot): daily bars, defaults (12/26/9 EMA, MACD x Signal), long and short, slippage 0 on the pinelib side (indep's reference has no slippage). MACD = EMA12 - EMA26 of close, signal = EMA9 of MACD
(seeded once 9 valid MACD values exist); a cross over goes long, a cross under goes short, each reversing at the next open."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "EmvVsgot"


def check():
    df = bars(8000, seed=3)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    macd = np_ema(c, 12) - np_ema(c, 26)
    sig = np_ema(macd, 9)
    up, dn = np_cross_over(macd, sig), np_cross_under(macd, sig)

    def orders(i, pos):
        out = []
        if up[i]:
            out.append(("entry", 1))
        if dn[i]:
            out.append(("entry", -1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
