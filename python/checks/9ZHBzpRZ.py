"""Independent check — SERHAN1 WMA+RSI Trailing Scalp (9ZHBzpRZ): 5-min bars. WMA 9/21 cross with the close beyond both
and RSI on the right side of 50; exit is a trailing stop re-issued every bar in a position: activation = entry +/-
(close*1.5%/mintick) ticks, offset 0 (stop sits on the best price reached). Uses indep.exit_hit's trailing model.
The date filter is opened (start = 0) on both sides because the synthetic bars start in 2015."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_rsi, np_wma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "9ZHBzpRZ"


def check():
    df = bars(20000, seed=81, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    f, s, rsi = np_wma(c, 9), np_wma(c, 21), np_rsi(c, 14)
    with np.errstate(invalid="ignore"):
        lgo = np_cross_over(f, s) & (c > f) & (c > s) & (rsi > 50)
        sgo = np_cross_under(f, s) & (c < f) & (c < s) & (rsi < 50)

    def trail(i, pos, ep, eb):
        return (c[i - 1] * 0.015 / 0.01, 0.0) if i > eb else None

    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if lgo[i] else []) + ([("entry", -1)] if sgo[i] else []),
                   trail=trail, tick=0.01)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params={"Başlangıç Tarihi": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
