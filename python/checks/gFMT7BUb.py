"""Independent check — KALKI TFXBOT (gFMT7BUb): daily bars, process_orders_on_close, one position (reversals). Swing low / high with 10 bars left (strict) and 3 right; latest confirmed values are floor / ceiling. Sweep buy: low < floor,
close > floor, up bar, close > EMA200, position <= 0 -> close any short and go long at the close; stop = low - 0.05, target = close + 3 x (close - stop), fixed at the signal bar and working from the next bar. Sweep sell mirrors
(stop = high + 0.05). Margin and slippage off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "gFMT7BUb"


def pivots(x, L, R, high):
    n = len(x)
    out = np.full(n, np.nan)
    for i in range(L + R, n):
        p = i - R
        left, right = x[p - L:p], x[p + 1:p + R + 1]
        if high:
            if all(x[p] > left) and all(x[p] >= right):
                out[i] = x[p]
        else:
            if all(x[p] < left) and all(x[p] <= right):
                out[i] = x[p]
    return out


def check():
    df = bars(6000, seed=577)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    sup = pd.Series(pivots(l, 10, 3, False)).ffill().to_numpy()
    res = pd.Series(pivots(h, 10, 3, True)).ffill().to_numpy()
    ema = np_ema(c, 200)
    with np.errstate(invalid="ignore"):
        sb = (l < sup) & (c > sup) & (c > o) & (c > ema)
        ss = (h > res) & (c < res) & (c < o) & (c < ema)
    lv = {1: None, -1: None}

    def orders(i, pos):
        out = []
        if sb[i] and pos <= 0:
            if pos < 0:
                out.append(("close", -1))
            sl = l[i] - 0.05
            lv[1] = (sl, c[i] + (c[i] - sl) * 3.0)
            out.append(("entry", 1))
        if ss[i] and pos >= 0:
            if pos > 0:
                out.append(("close", 1))
            sl = h[i] + 0.05
            lv[-1] = (sl, c[i] - (sl - c[i]) * 3.0)
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
