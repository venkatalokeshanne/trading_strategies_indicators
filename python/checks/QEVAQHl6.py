"""Independent check — SPY 200SMA +4% / -3% (QEVAQHl6): daily bars (the 1995 start date precedes the data). A close above SMA200 * 1.04 enters long when flat; a close below SMA200 * 0.97 closes it at the next open."""
import numpy as np

from indep import bars, compare, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "QEVAQHl6"


def check():
    df = bars(6000, seed=257)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    s = np_sma(c, 200)
    with np.errstate(invalid="ignore"):
        en, ex = c > s * 1.04, c < s * 0.97
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if en[i] and pos == 0 else []) + ([("close", 1)] if ex[i] and pos > 0 else []))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
