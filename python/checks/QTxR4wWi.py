"""Independent check — Three Muskateers (QTxR4wWi): daily bars, Trade Direction "Both" (passed to both sides). Votes: EMA50 > EMA200 (bear: <), RSI14 crossing over 30 (bear: under 70), close crossing over the lower BB(20, 2) (bear: under the upper band, population stdev); two or more votes = signal.
Buy while not long -> long, sell while not short -> short (a reversal at the next open)."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "QTxR4wWi"


def check():
    df = bars(9000, seed=19)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    rsi = np_rsi(c, 14)
    f, s = np_ema(c, 50), np_ema(c, 200)
    basis = np_sma(c, 20)
    dev = 2.0 * pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    with np.errstate(invalid="ignore"):
        bc = (f > s).astype(int) + np_cross_over(rsi, 30.0).astype(int) + np_cross_over(c, basis - dev).astype(int)
        sc = (f < s).astype(int) + np_cross_under(rsi, 70.0).astype(int) + np_cross_under(c, basis + dev).astype(int)

    def orders(i, pos):
        out = []
        if bc[i] >= 2 and pos <= 0:
            out.append(("entry", 1))
        if sc[i] >= 2 and pos >= 0:
            out.append(("entry", -1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Trade Direction": "Both"},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
