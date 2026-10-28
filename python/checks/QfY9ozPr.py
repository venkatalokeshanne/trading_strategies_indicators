"""Independent check — 21/75 EMA Cross Filtered Long Only (QfY9ozPr): daily bars. Double-smoothed EMAs (EMA(EMA(close,20),100) vs
EMA(EMA(close,70),100)); long on a cross-up when flat, close on cross-down; hard stop 10 % under the average price re-issued every
bar (na while flat), so it works from the bar after the fill. Sizing (4x equity) does not change prices and is not compared."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "QfY9ozPr"


def check():
    df = bars(6000, seed=93)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    fast, slow = np_ema(np_ema(c, 20), 100), np_ema(np_ema(c, 70), 100)
    up, dn = np_cross_over(fast, slow), np_cross_under(fast, slow)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if up[i] and pos == 0 else []) + ([("close", 1)] if dn[i] else []),
                   stop=lambda i, pos, ep, eb: ep * 0.9 if i > eb else None)
    sym = SymbolInfo.make("AMEX:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D"), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
