"""Independent check — Simple Smart Buy/Sell (IaAxlKab): 5-min bars, session VWAP(close) + EMA 9/20 trend,
pullback to EMA9 and break of the prior bar's extreme. The two strategy.exit calls run on EVERY bar, so the
bracket working on bar i is bar i-1's (close -/+ ATR, close +/- 2 ATR), including on the fill bar."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, np_vwap, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "IaAxlKab"


def check():
    df = bars(20000, seed=78, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    e9, e20, vw, atr = np_ema(c, 9), np_ema(c, 20), np_vwap(df, c), np_atr(h, l, c, 14)
    ph, pl = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    with np.errstate(invalid="ignore"):
        buy = (c > vw) & (e9 > e20) & (l <= e9) & (c > ph)
        sell = (c < vw) & (e9 < e20) & (h >= e9) & (c < pl)

    def stop(i, pos, ep, eb):
        return (c[i - 1] - atr[i - 1] if pos > 0 else c[i - 1] + atr[i - 1]) if i > 0 else None

    def target(i, pos, ep, eb):
        return (c[i - 1] + 2 * atr[i - 1] if pos > 0 else c[i - 1] - 2 * atr[i - 1]) if i > 0 else None

    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if buy[i] else []) + ([("entry", -1)] if sell[i] else []),
                   stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
