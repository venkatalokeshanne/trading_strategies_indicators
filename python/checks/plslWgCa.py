"""Independent check — SuperTrend Bot v6 (plslWgCa): hourly bars. np_supertrend(3, 10) direction flip -1 (from 1) buys, flip to 1 (from -1) sells short (reversing, 1 contract). Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_supertrend, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "plslWgCa"


def check():
    df = bars(30000, seed=308, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    _, d = np_supertrend(h, l, c, 3.0, 10)
    d1 = np.r_[np.nan, d[:-1]]
    with np.errstate(invalid="ignore"):
        buy, sell = (d == -1) & (d1 == 1), (d == 1) & (d1 == -1)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if buy[i] else []) + ([("entry", -1)] if sell[i] else []))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
