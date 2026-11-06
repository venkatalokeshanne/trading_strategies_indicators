"""Independent check — Surgical Sweep (25Ffpyo0): 5% of equity per trade on the pinelib side (100% with no stops goes bust on synthetic data; sizing never changes trade prices); daily bars (7 days a week, so the weekday filter matters; day of week from the New York calendar date of the bar's open). Latest confirmed pivot high / low (5 bars each
side, centre strictly highest / lowest) = resistance / support. Sell: prior high and close above resistance, close back below, volume > 1.2 x SMA20(volume). Buy: mirror. Weekday signals enter at the next open and reverse; no exits."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "25Ffpyo0"


def check():
    df = bars(6000, seed=12)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    k = 5
    dow = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York").dt.dayofweek.to_numpy()
    weekday = dow < 5
    hv = v > np_sma(v, 20) * 1.2
    res = np.full(n, np.nan)
    sup = np.full(n, np.nan)
    r = s = np.nan
    for i in range(n):
        if i >= 2 * k:
            m = i - k
            win = h[m - k:m + k + 1]
            if h[m] == win.max() and (win == h[m]).sum() == 1:
                r = h[m]
            win = l[m - k:m + k + 1]
            if l[m] == win.min() and (win == l[m]).sum() == 1:
                s = l[m]
        res[i], sup[i] = r, s
    with np.errstate(invalid="ignore"):
        sell = np.r_[False, (h[:-1] > res[1:]) & (c[:-1] > res[1:])] & (c < res) & hv
        buy = np.r_[False, (l[:-1] < sup[1:]) & (c[:-1] < sup[1:])] & (c > sup) & hv

    def orders(i, pos):
        out = []
        if buy[i] and weekday[i]:
            out.append(("entry", 1))
        if sell[i] and weekday[i]:
            out.append(("entry", -1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "default_qty_value": 5}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
