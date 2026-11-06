"""Independent check — DMT Universal (i0XSbToM): daily bars, defaults (EMA cross on, RSI filter off, EMA200 trend filter on). EMA9 over EMA21 with the close above EMA200 goes long, under with the close below goes short (reversing)."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "i0XSbToM"


def check():
    df = bars(6000, seed=281)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    f, s, t = np_ema(c, 9), np_ema(c, 21), np_ema(c, 200)
    with np.errstate(invalid="ignore"):
        ls, ss = np_cross_over(f, s) & (c > t), np_cross_under(f, s) & (c < t)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if ls[i] else []) + ([("entry", -1)] if ss[i] else []))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
