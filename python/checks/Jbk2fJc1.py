"""Independent check — Allah's Compass (Jbk2fJc1): daily bars, Stop Loss % = 3 here (passed to both sides). BB%B (20, 2, population stdev) crossing up through 0 enters long when flat and sets stop = close*(1-3%); a bullish divergence
(close < close[10], %B > %B[10], %B < 0.2, newly true) while long lowers the stop (its Long_Add entry is ignored: pyramiding 1; math.min with na stays na); close <= stop while long or %B >= 1 closes everything at the next open."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "Jbk2fJc1"
SLP = 3.0


def check():
    df = bars(8000, seed=44)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    basis = np_sma(c, 20)
    dev = 2.0 * pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        pct = (c - (basis - dev)) / ((basis + dev) - (basis - dev))
        cig = np_cross_over(pct, 0.0)
        pp = np.r_[[np.nan] * 10, pct[:-10]]
        pc = np.r_[[np.nan] * 10, c[:-10]]
        bd = (c < pc) & (pct > pp) & (pct < 0.2)
    bd_prev = np.r_[False, bd[:-1]]
    stop = [np.nan]

    def orders(i, pos):
        out = []
        if cig[i] and pos == 0:
            out.append(("entry", 1))
            stop[0] = c[i] * (1 - SLP / 100)
        if bd[i] and not bd_prev[i] and pos > 0:
            stop[0] = np.nan if np.isnan(stop[0]) else min(stop[0], c[i] * (1 - SLP / 100))
        with np.errstate(invalid="ignore"):
            if pos > 0 and c[i] <= stop[0]:
                out.append(("close_all",))
                stop[0] = np.nan
        if pct[i] >= 1.0 and pos > 0:
            out.append(("close_all",))
            stop[0] = np.nan
        return out

    ref = simulate(o, h, l, c, lambda i, pos: [(("close", 1) if x == ("close_all",) else x) for x in orders(i, pos)])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Stop Loss %": SLP},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
