"""Independent check — Qing LRC (ZDhizQgu): daily bars, orders at the signal close (process_orders_on_close). Channel mid = least-squares line value at the last of 20 closes (numpy polyfit), dev = population stdev(20), bands +/- 1.618 dev. Long when upper band > EMA20
and (low <= lower band or low <= 1.02 x latest confirmed pivot low (5/5)) and close > open and no trade is open; exit when lower band < EMA20 or high >= upper band (only if long)."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "ZDhizQgu"


def check():
    df = bars(8000, seed=36)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    mid = np.full(n, np.nan)
    x = np.arange(20)
    for i in range(19, n):
        b, a = np.polyfit(x, c[i - 19:i + 1], 1)
        mid[i] = a + b * 19
    dev = pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    up, lo = mid + 1.618 * dev, mid - 1.618 * dev
    e20 = np_ema(c, 20)
    sup = np.full(n, np.nan)
    s = np.nan
    for i in range(n):
        if i >= 10:
            m = i - 5
            w = l[m - 5:m + 6]
            if l[m] == w.min() and (w == l[m]).sum() == 1:
                s = l[m]
        sup[i] = s
    with np.errstate(invalid="ignore"):
        buy = (up > e20) & ((l <= lo) | (l <= sup * 1.02)) & (c > o)
        ex = (lo < e20) | (h >= up)

    def orders(i, pos):
        out = []
        if buy[i] and pos == 0:
            out.append(("entry", 1))
        if ex[i] and pos > 0:
            out.append(("close", 1))
        return out

    ref = simulate(o, h, l, c, orders, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
