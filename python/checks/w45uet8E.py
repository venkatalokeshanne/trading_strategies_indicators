"""Independent check — 单因子指数增强 (w45uet8E): hourly bars, long only. Daily SMA60 / SMA100 of the day's last close (days from 09:30, np_periods), lookahead ON (every chart bar of a day sees the day's final values);
golden-cross regime must hold 15 consecutive chart bars; z = (close - SMA24) / max(population stdev24, 0.0001): z < -2.1 in regime arms, z > 1.1 / lost regime / close < 97 % of the entry price disarms; armed + flat enters at the
next open, disarmed + long closes at the next open (the entry price is the next-open fill). Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_periods, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "w45uet8E"


def check():
    df = bars(60000, seed=247, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    pid, _ = np_periods(df, 1440)
    dc = pd.Series(c).groupby(pid).last().to_numpy()
    ms, ml = np_sma(dc, 60)[pid], np_sma(dc, 100)[pid]                 # lookahead on: the period's final value on every bar
    mean = np_sma(c, 24)
    sd = pd.Series(c).rolling(24).std(ddof=0).to_numpy()
    with np.errstate(invalid="ignore"):
        z = (c - mean) / np.maximum(sd, 0.0001)
        raw = ms > ml
    cnt, armed, ep = 0, False, [np.nan]

    def orders(i, pos):
        nonlocal cnt, armed
        cnt = cnt + 1 if raw[i] else 0
        regime = cnt >= 15
        stop = pos > 0 and c[i] < ep[0] * 0.97
        if regime and z[i] < -2.1:
            armed = True
        if z[i] > 1.1 or (not regime) or stop:
            armed = False
        out = []
        if armed and pos == 0:
            out.append(("entry", 1))
            ep[0] = o[i + 1] if i + 1 < n else np.nan                    # next-open fill
        if (not armed) and pos > 0:
            out.append(("close", 1))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
