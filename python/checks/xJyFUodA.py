"""Independent check — EMA + S/R Breakout (xJyFUodA): daily bars. Close crossing over the highest high of the previous 20 bars with EMA9 > EMA20 goes long; crossing under the lowest low of the previous 20 bars with EMA9 < EMA20
goes short (reversing). While a position is open at a close: target 12 % / stop 6 % around the entry price, working from the next bar. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "xJyFUodA"


def check():
    df = bars(8000, seed=271)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    f, s = np_ema(c, 9), np_ema(c, 20)
    res = pd.Series(h).shift(1).rolling(20).max().to_numpy()
    sup = pd.Series(l).shift(1).rolling(20).min().to_numpy()
    with np.errstate(invalid="ignore"):
        ls, ss = np_cross_over(c, res) & (f > s), np_cross_under(c, sup) & (f < s)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if ls[i] else []) + ([("entry", -1)] if ss[i] else []),
                   stop=lambda i, pos, ep, eb: None if eb >= i else ep * (1 - 0.06 * pos),
                   target=lambda i, pos, ep, eb: None if eb >= i else ep * (1 + 0.12 * pos))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
