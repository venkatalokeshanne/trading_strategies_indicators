"""Independent check — EMA 20/55 flip (x9pPfwmI): 5-min bars; golden cross = long, death cross = short, reversing, no exits."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "x9pPfwmI"


def check():
    df = bars(12000, seed=110, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    f, s = np_ema(c, 20), np_ema(c, 55)
    up, dn = np_cross_over(f, s), np_cross_under(f, s)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if up[i] else []) + ([("entry", -1)] if dn[i] else []))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
