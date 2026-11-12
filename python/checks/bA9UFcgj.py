"""Independent check — SPY Bear Regime Short (bA9UFcgj): daily bars, short only. Close < SMA250 by at least 2 % and > SMA5 with the 3-bar RSI crossing over 70 shorts when flat; a close under SMA5 or above SMA250 covers at the next
open. Slippage (1 tick) and margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_cross_over, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "bA9UFcgj"


def check():
    df = bars(12000, seed=273)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    s250, s5, rsi = np_sma(c, 250), np_sma(c, 5), np_rsi(c, 3)
    with np.errstate(invalid="ignore"):
        en = (c < s250) & (c > s5) & np_cross_over(rsi, 70.0) & (c <= s250 * 0.98)
        ex = (c < s5) | (c > s250)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", -1)] if en[i] and pos == 0 else []) + ([("close", -1)] if ex[i] and pos < 0 else []))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
