"""Independent check — BS Proyeccion TP/SL (fqS79J4w): 5-minute bars (24h synthetic), process_orders_on_close, one position (entries reverse), trade list only. Higher timeframe 15 minutes (09:30-NY blocks): resistance / support = the PREVIOUS
15-minute bar's high / low, seen by every chart bar of the current period (lookahead on). Support zone = low <= support x 1.001 within the last 5 bars (barssince <= 5, na before the first touch), resistance zone = high >= resistance x 0.999.
Long: zone touched recently and the close crosses over EMA5 (short: under). Entry at the close with TP +/-0.2% and SL -/+0.1% of the close, fixed at the signal and re-issued on any signal (also when the side is already open); working from the next bar.
Margin and slippage off, size per the script (qty tiny) on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, np_periods, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "fqS79J4w"


def barssince(cond):
    out = np.full(len(cond), np.nan)
    last = None
    for i, x in enumerate(cond):
        if x:
            last = i
        if last is not None:
            out[i] = i - last
    return out


def check():
    df = bars(20000, seed=757, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    pid, last_of = np_periods(df, 15)
    npd = pid[-1] + 1
    ph = np.array([h[pid == k].max() for k in range(npd)])
    pl = np.array([l[pid == k].min() for k in range(npd)])
    res = np.full(n, np.nan)
    sup = np.full(n, np.nan)
    for i in range(n):
        if pid[i] >= 1:
            res[i], sup[i] = ph[pid[i] - 1], pl[pid[i] - 1]
    ema = np_ema(c, 5)
    with np.errstate(invalid="ignore"):
        bs_s = barssince(l <= sup * 1.001)
        bs_r = barssince(h >= res * 0.999)
        lc = (bs_s <= 5) & np_cross_over(c, ema)
        sc = (bs_r <= 5) & np_cross_under(c, ema)
    lv = {1: None, -1: None}

    def orders(i, pos):
        out = []
        if lc[i]:
            lv[1] = (c[i] * (1 - 0.001), c[i] * (1 + 0.002))
            out.append(("entry", 1))
        if sc[i]:
            lv[-1] = (c[i] * (1 + 0.001), c[i] * (1 - 0.002))
            out.append(("entry", -1))
        return out

    def stop(i, pos, ep, eb):
        return lv[pos][0] if lv[pos] else None

    def target(i, pos, ep, eb):
        return lv[pos][1] if lv[pos] else None

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
