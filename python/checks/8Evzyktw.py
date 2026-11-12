"""Independent check — Strategy 461 TS M15 (8Evzyktw): daily bars, process_orders_on_close, one position, trade list only. Clean bullish turtle soup: previous candle bearish, low < previous low, high <= previous high, close > open,
close > previous low; bearish mirrored. EMA200 bias. When flat: stop = low - 0.2 (20 ticks), target = close + R x risk (R = 1), fixed at the signal bar (re-issued unchanged) and working from the next bar. Margin and slippage off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "8Evzyktw"


def check():
    df = bars(6000, seed=266)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ema = np_ema(c, 200)
    o1, c1, h1, l1 = (np.r_[np.nan, x[:-1]] for x in (o, c, h, l))
    with np.errstate(invalid="ignore"):
        lb = (c1 < o1) & (l < l1) & ~(h > h1) & (c > o) & (c > l1) & (c > ema)
        sb = (c1 > o1) & (h > h1) & ~(l < l1) & (c < o) & (c < h1) & (c < ema)
    lv = {1: None, -1: None}

    def orders(i, pos):
        out = []
        if pos == 0 and lb[i] and (c[i] - (l[i] - 0.2)) > 0:
            sl = l[i] - 0.2
            lv[1] = (sl, c[i] + (c[i] - sl) * 1.0)
            out.append(("entry", 1))
        if pos == 0 and sb[i] and ((h[i] + 0.2) - c[i]) > 0:
            sl = h[i] + 0.2
            lv[-1] = (sl, c[i] - (sl - c[i]) * 1.0)
            out.append(("entry", -1))
        return out

    def stop(i, pos, ep, eb):
        return lv[pos][0] if lv[pos] else None

    def target(i, pos, ep, eb):
        return lv[pos][1] if lv[pos] else None

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
