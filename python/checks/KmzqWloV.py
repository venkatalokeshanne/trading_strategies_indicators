"""Independent check — TWE 2-Bar Break (KmzqWloV): 5-min bars. High above the previous two bars' high with the close over EMA50 = long, low under their
low below EMA50 = short (reversing; the close() of the other side only acts if that trade is open); an open position also closes when the opposite
extreme of the previous two bars breaks. No brackets."""
import numpy as np

from indep import bars, compare, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "KmzqWloV"


def check():
    df = bars(20000, seed=143, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    e = np_ema(c, 50)
    h1, h2 = np.r_[np.nan, h[:-1]], np.r_[[np.nan] * 2, h[:-2]]
    l1, l2 = np.r_[np.nan, l[:-1]], np.r_[[np.nan] * 2, l[:-2]]
    thi, tlo = np.fmax(h1, h2), np.fmin(l1, l2)
    thi[np.isnan(h1) | np.isnan(h2)] = np.nan
    tlo[np.isnan(l1) | np.isnan(l2)] = np.nan
    with np.errstate(invalid="ignore"):
        buy, sell = (h > thi) & (c > e), (l < tlo) & (c < e)

    def orders(i, pos):
        out = []
        if buy[i] and pos <= 0:
            if pos < 0:
                out.append(("close", -1))
            out.append(("entry", 1))
        if sell[i] and pos >= 0:
            if pos > 0:
                out.append(("close", 1))
            out.append(("entry", -1))
        if pos > 0 and l[i] < tlo[i]:
            out.append(("close", 1))
        if pos < 0 and h[i] > thi[i]:
            out.append(("close", -1))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
