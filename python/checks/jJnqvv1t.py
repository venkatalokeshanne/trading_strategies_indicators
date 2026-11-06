"""Independent check — High Beta RSI Reversal (jJnqvv1t): 5-min New York bars. RSI<25 / >75 capitulation
with volume 1.5x its SMA(20) and a close beyond the prior bar's extreme; exit at the session VWAP or when
the close breaks the entry bar's low/high (var stop persists between trades)."""
import numpy as np

from indep import bars, compare, np_rsi, np_sma, np_vwap, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "jJnqvv1t"
LO, HI = 40, 60       # looser than the 25/75 defaults so the check sees enough trades (passed to both sides)


def check():
    df = bars(20000, seed=73, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    rsi, vma, vw = np_rsi(c, 14), np_sma(v, 20), np_vwap(df, c)
    ph, pl = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    with np.errstate(invalid="ignore"):
        lc = (rsi < LO) & (v > vma * 1.5) & (c > ph)
        sc = (rsi > HI) & (v > vma * 1.5) & (c < pl)
    lstop, sstop = np.nan, np.nan
    stops = []                                   # (long_stop, short_stop) as of the end of bar i's entry block
    for i in range(len(c)):
        if lc[i]:
            lstop = l[i]
        if sc[i]:
            sstop = h[i]
        stops.append((lstop, sstop))

    def orders(i, pos):
        out = []
        if lc[i]:
            out.append(("entry", 1))
        if sc[i]:
            out.append(("entry", -1))
        ls, ss = stops[i]
        if pos > 0 and (c[i] >= vw[i] or c[i] < ls):
            out.append(("close", 1))
        if pos < 0 and (c[i] <= vw[i] or c[i] > ss):
            out.append(("close", -1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)   # synthetic prices drift past 10 % of equity
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params={"input 2": LO, "input 3": HI}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
