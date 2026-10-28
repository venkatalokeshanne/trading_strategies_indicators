"""Independent check — How To Set Backtest Time Ranges (xAEG4ZJG): daily bars, From Year 2015 so the whole sample is inside the window. SMA14 crossing over SMA28 enters long (cash sized, one trade at a time),
the cross under closes it; both at the next open, sessions 0000-0000 = any time."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "xAEG4ZJG"


def check():
    df = bars(5000, seed=5)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    a, b = np_sma(c, 14), np_sma(c, 28)
    up, dn = np_cross_over(a, b), np_cross_under(a, b)

    def orders(i, pos):
        out = []
        if up[i]:
            out.append(("entry", 1))
        if dn[i] and pos > 0:
            out.append(("close", 1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"From Year": 2015},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
