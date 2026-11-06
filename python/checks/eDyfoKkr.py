"""Independent check — Joey Strategy (eDyfoKkr): daily bars. %K = SMA3(stoch14), %D = SMA3(%K); a %K cross over %D with %K < 30 while flat goes long. At the close of the first bar with the position open, the entry price and that bar's
ATR14 fix the levels entry +/- 1.5 ATR; the bracket is issued from that close on, so it first works on the NEXT bar (not on the fill bar)."""
import numpy as np

from indep import bars, compare, np_atr, np_cross_over, np_sma, np_stoch, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "eDyfoKkr"


def check():
    df = bars(6000, seed=210)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    k = np_sma(np_stoch(c, h, l, 14), 3)
    d = np_sma(k, 3)
    atr = np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        sig = np_cross_over(k, d) & (k < 30)

    def stop(i, pos, ep, eb):
        return None if eb >= i else ep - 1.5 * atr[eb]

    def target(i, pos, ep, eb):
        return None if eb >= i else ep + 1.5 * atr[eb]

    ref = simulate(o, h, l, c, lambda i, pos: [("entry", 1)] if sig[i] and pos == 0 else [], stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
