"""Independent check — @santoshpsiii Crypto Algo (9x9ohJ2R): hourly bars. np_supertrend(3, 10) flipping to up (-1) while BB width ((upper - lower) / basis, 20, 2 pop-stdev) > its SMA20 buys; flipping to down (+1) while trending sells short;
each flip also closes the opposite side whether or not it is trending. Queued in source order: entry Long, close Long, entry Short, close Short. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_sma, np_supertrend, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "9x9ohJ2R"


def check():
    df = bars(30000, seed=306, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    _, d = np_supertrend(h, l, c, 3.0, 10)
    d1 = np.r_[np.nan, d[:-1]]
    basis = np_sma(c, 20)
    sd = pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    bbw = 4 * sd / basis
    with np.errstate(invalid="ignore"):
        trend = bbw > np_sma(bbw, 20)
    chg = np.r_[False, (d[1:] != d[:-1]) & ~np.isnan(d1[1:])]

    def orders(i, pos):
        out = []
        if trend[i] and chg[i] and d[i] == -1:
            out.append(("entry", 1))
        if chg[i] and d[i] == 1:
            out.append(("close", 1))
        if trend[i] and chg[i] and d[i] == 1:
            out.append(("entry", -1))
        if chg[i] and d[i] == -1:
            out.append(("close", -1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
