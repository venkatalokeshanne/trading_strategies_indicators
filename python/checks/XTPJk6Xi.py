"""Independent check — BTC 多空双向趋势系统 (XTPJk6Xi): hourly bars. np_supertrend(3, 10) flipping to up with close > EMA200 goes long, flipping to down below EMA200 short (reversing). While a position is open at the close, a
trailing exit with activation 3 % and offset 1.5 % of the entry price (rounded half up to ticks of 0.01) works from the next bar; a direction against the position closes it at the next open. Margin off on the pinelib side."""
import math

import numpy as np

from indep import bars, compare, np_ema, np_supertrend, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "XTPJk6Xi"
TICK = 0.01


def check():
    df = bars(30000, seed=251, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    e = np_ema(c, 200)
    _, d = np_supertrend(h, l, c, 3.0, 10)
    d1 = np.r_[np.nan, d[:-1]]
    with np.errstate(invalid="ignore"):
        lc, sc = (c > e) & (d < 0) & (d1 > 0), (c < e) & (d > 0) & (d1 < 0)

    def orders(i, pos):
        out = []
        if lc[i]:
            out.append(("entry", 1))
        if sc[i]:
            out.append(("entry", -1))
        if pos > 0 and d[i] > 0:
            out.append(("close", 1))
        if pos < 0 and d[i] < 0:
            out.append(("close", -1))
        return out

    def trail(i, pos, ep, eb):
        if eb >= i:
            return None
        return (math.floor(ep * 3.0 / 100 / TICK + 0.5), math.floor(ep * 1.5 / 100 / TICK + 0.5))

    ref = simulate(o, h, l, c, orders, trail=trail, tick=TICK)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
