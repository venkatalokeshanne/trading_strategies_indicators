"""Independent check — Nifty 10-Candle ORB v4 (cMy2aLGD; Iw8elpH5 / vQjYETM7 / cMy2aLGD are the same script, exit minute 15 here): 5-min New York bars. The first 10 bars of each trading day (days from 09:30) give the range
high / low. Once 10 bars have passed, flat, before 15:00, a close crossing over the range high goes long (under the low: short) unless the last trade that day was the same direction. While a position is open at a close, a 1 % target and
0.5 % stop around the entry price are issued (working from the next bar). From 15:15 on, every bar closes an open position at the next open. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_periods, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "cMy2aLGD"
EXIT_MIN = 15


def check():
    df = bars(40000, seed=268, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    hm = (ny.dt.hour * 100 + ny.dt.minute).to_numpy()
    day, _ = np_periods(df, 1440)
    hi = lo = np.nan
    idx, last = 0, 0
    hs, ls_ = np.full(n, np.nan), np.full(n, np.nan)
    st = dict(idx=0, last=0)
    for i in range(n):
        if i == 0 or day[i] != day[i - 1]:
            hi = lo = np.nan
            st["idx"] = 0
        if st["idx"] < 10:
            st["idx"] += 1
            hi = h[i] if np.isnan(hi) else max(hi, h[i])
            lo = l[i] if np.isnan(lo) else min(lo, l[i])
        hs[i], ls_[i] = hi, lo
    cross_up = np.r_[False, (c[1:] > hs[1:]) & (c[:-1] <= hs[:-1])]
    cross_dn = np.r_[False, (c[1:] < ls_[1:]) & (c[:-1] >= ls_[:-1])]
    exit_t, enter_ok = hm >= 1500 + EXIT_MIN, hm < 1500
    idx_at = np.zeros(n, int)
    k = 0
    for i in range(n):
        if i == 0 or day[i] != day[i - 1]:
            k = 0
        if k < 10:
            k += 1
        idx_at[i] = k
    state = dict(last=0)

    def orders(i, pos):
        if i == 0 or day[i] != day[i - 1]:
            state["last"] = 0
        out = []
        ok = idx_at[i] >= 10 and pos == 0 and enter_ok[i] and not exit_t[i]
        with np.errstate(invalid="ignore"):
            if ok and cross_up[i] and state["last"] <= 0:
                out.append(("entry", 1)); state["last"] = 1
            if ok and cross_dn[i] and state["last"] >= 0:
                out.append(("entry", -1)); state["last"] = -1
        if exit_t[i] and pos != 0:
            out.append(("close", pos))
        return out

    ref = simulate(o, h, l, c, orders,
                   stop=lambda i, pos, ep, eb: None if eb >= i else ep * (1 - 0.005 * pos),
                   target=lambda i, pos, ep, eb: None if eb >= i else ep * (1 + 0.01 * pos))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
