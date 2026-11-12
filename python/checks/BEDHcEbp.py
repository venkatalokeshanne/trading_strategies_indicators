"""Independent check — Smart Money AOI (BEDHcEbp): 5-min bars, 1h security (09:30-NY blocks, lookahead off). bullBOS = close > highest(high,10)[1]; bearBOS = close < lowest(low,10)[1]; bull FVG = low > high[2], bear FVG = high < low[2].
Long when bullBOS & close > HTF low & bull FVG; short when bearBOS & close < HTF high & bear FVG; market entries at the next open reversing an open opposite trade."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_periods, np_security_lookahead_off, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "BEDHcEbp"


def check():
    df = bars(12000, seed=88, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    hh = pd.Series(h).rolling(10).max().to_numpy()
    ll = pd.Series(l).rolling(10).min().to_numpy()
    pid, last_of = np_periods(df, 60)
    ph = pd.Series(h).groupby(pid).max().to_numpy()
    pl = pd.Series(l).groupby(pid).min().to_numpy()
    th, tl = np_security_lookahead_off(ph, pid, last_of), np_security_lookahead_off(pl, pid, last_of)
    hh1, ll1 = np.r_[np.nan, hh[:-1]], np.r_[np.nan, ll[:-1]]
    h2, l2 = np.r_[[np.nan] * 2, h[:-2]], np.r_[[np.nan] * 2, l[:-2]]
    with np.errstate(invalid="ignore"):
        lg = (c > hh1) & (c > tl) & (l > h2)
        sh = (c < ll1) & (c < th) & (h < l2)

    def orders(i, pos):
        out = []
        if lg[i]:
            out.append(("entry", 1))
        if sh[i]:
            out.append(("entry", -1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
