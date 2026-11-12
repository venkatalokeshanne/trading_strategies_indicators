"""Independent check — Donchian Breakout with ATR Trailing Stop (NeEiwmDq): hourly bars (24h synthetic, UTC), process_orders_on_close, long only, trade list only. Long when the close is above the previous 20 bars' highest high and above EMA200, unless it is a
Friday (UTC) bar from 20:00 on (those bars also close any position), needing ATR14 (the sizing is na before it exists). Entry at the close. On the first script run with the position (the bar after the fill): trail distance = 2.5 x the CURRENT ATR14, stop = fill price -
distance; later runs: stop = max(stop, high - that distance); the stop is re-issued every run and works from the next bar. Margin and slippage off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "NeEiwmDq"


def check():
    df = bars(20000, seed=478, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ut = pd.to_datetime(df["time"], unit="ms", utc=True)
    fri = ((ut.dt.dayofweek == 4) & (ut.dt.hour >= 20)).to_numpy()
    up = np.r_[np.nan, pd.Series(h).rolling(20, min_periods=20).max().to_numpy()[:-1]]
    ema = np_ema(c, 200)
    atr = np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        sig = (c > up) & (c > ema) & ~fri & ~np.isnan(atr)
    S = dict(stop=np.nan, dist=np.nan, prev=0)
    poscl = np.zeros(n)
    stop_arr = np.full(n, np.nan)
    ep_now = {"i": -1, "ep": np.nan}

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if sig[i] and pos == 0:
            out.append(("entry", 1))
        just = pos > 0 and S["prev"] <= 0
        if just:
            S["dist"] = atr[i] * 2.5
            S["stop"] = ep_now["ep"] - S["dist"]
        elif pos > 0:
            S["stop"] = max(S["stop"], h[i] - S["dist"])
        if pos > 0:
            stop_arr[i] = S["stop"]
        if pos == 0:
            S["stop"] = S["dist"] = np.nan
        if fri[i] and pos != 0:
            out.append(("close", pos))
        S["prev"] = pos
        return out

    def stop(i, pos, ep, eb):
        ep_now["i"], ep_now["ep"] = i, ep
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(stop_arr[i - 1]):
            return None
        return stop_arr[i - 1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
