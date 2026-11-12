"""Independent check — Gold Pro EMA Cross (ZrdRGzl3): 5-min bars. EMA 9/21 cross reverses; each entry carries strategy.exit(loss, profit)
in TICKS (mintick 0.01) from the entry price, issued on the signal bar so it works from the fill bar. The tick inputs are scaled down
(100 / 200 = $1 / $2) so the synthetic prices reach them."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "ZrdRGzl3"
TP, SL = 200, 100


def check():
    df = bars(20000, seed=106, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    f, s = np_ema(c, 9), np_ema(c, 21)
    up, dn = np_cross_over(f, s), np_cross_under(f, s)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if up[i] else []) + ([("entry", -1)] if dn[i] else []),
                   stop=lambda i, pos, ep, eb: ep - pos * SL * 0.01, target=lambda i, pos, ep, eb: ep + pos * TP * 0.01)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params={"Take Profit (Points)": TP, "Stop Loss (Points)": SL}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
