"""Independent check — SuperTrend Long/Short (ZV6yfF87): hourly bars. np_supertrend(3, 10) direction flips (not on the first bar: change is na) close the other id and enter the new side (1 contract). While a long (short)
is open at the close and the SuperTrend line is below (above) the close, a stop at the line is issued; it stays in force for that trade after being issued (even when the condition later fails) and is dropped when the
trade ends. Slippage (3 ticks) and margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_supertrend, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "ZV6yfF87"


def check():
    df = bars(30000, seed=250, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    line, d = np_supertrend(h, l, c, 3.0, 10)
    line = line.copy()
    line[0] = np.nan
    levels, cur = {}, [None]

    def orders(i, pos):
        out = []
        chg = i > 0 and d[i] != d[i - 1]
        if chg and d[i] < 0:
            out += [("close", -1), ("entry", 1)]
        if chg and d[i] > 0:
            out += [("close", 1), ("entry", -1)]
        if pos > 0 and not np.isnan(line[i]) and line[i] < c[i] and cur[0] is not None:
            levels[cur[0]] = line[i]
        if pos < 0 and not np.isnan(line[i]) and line[i] > c[i] and cur[0] is not None:
            levels[cur[0]] = line[i]
        return out

    def stop(i, pos, ep, eb):
        cur[0] = eb                                   # the trade this bar belongs to
        return levels.get(eb)

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
