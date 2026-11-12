"""Independent check — Sensex 9:45 3-Trade Limit Breakout (9ivEXFNq): 5-min New York bars on a mean-reverting synthetic index (Ornstein-Uhlenbeck around 20000 so the 500-point grid is meaningful). The 09:45 bar fixes lower / upper =
floor / ceil(open / 500) * 500 and targets one grid beyond; 09:45-15:15 (bar start), flat, a close at or above the upper line goes long and at or below the lower line short (at most 3 trades per day, counter reset at 09:45); stop 100 points from the signal close, moved to
the average price once the extreme is 200 points in profit (at that bar's close); the exit (limit at the target of its side, stop at the stop var) is issued while a position is open at a close, working from the next bar; the
15:25 bar closes everything. Margin off on the pinelib side."""
import math

import numpy as np
import pandas as pd

from indep import compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "9ivEXFNq"


def ou_bars(n, seed, mu=20000.0, theta=0.002, sigma=25.0, freq="5min"):
    rng = np.random.default_rng(seed)
    x = np.empty(n)
    x[0] = mu
    for i in range(1, n):
        x[i] = x[i - 1] + theta * (mu - x[i - 1]) + sigma * rng.normal()
    open_ = np.r_[x[0], x[:-1]] + rng.normal(0, 3, n)
    high = np.maximum(open_, x) + np.abs(rng.normal(0, 12, n))
    low = np.minimum(open_, x) - np.abs(rng.normal(0, 12, n))
    t = pd.date_range("2015-01-01", periods=n, freq=freq, tz="UTC").as_unit("ms").asi8
    return pd.DataFrame({"time": t, "open": open_, "high": high, "low": low, "close": x, "volume": rng.integers(1000, 100000, n).astype(float)})


def check():
    df = ou_bars(40000, 260)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    start, can, eod = m == 585, (m >= 585) & (m < 915), (m >= 925) & (m < 930)
    upper = lower = tpu = tpl = np.nan
    sl, trail = np.nan, False
    count = 0
    ep_now = {}
    store, poscl = [None] * n, np.zeros(n)

    def orders(i, pos):
        nonlocal upper, lower, tpu, tpl, sl, trail, count
        poscl[i] = pos
        if start[i]:
            lower = math.floor(o[i] / 500) * 500
            upper = math.ceil(o[i] / 500) * 500
            tpu, tpl, trail, count = upper + 500, lower - 500, False, 0
        with np.errstate(invalid="ignore"):
            cu = bool((not start[i]) and c[i] >= upper)
            cl = bool((not start[i]) and c[i] <= lower)
        out = []
        if cu and can[i] and pos == 0 and count < 3:
            out.append(("entry", 1)); sl = c[i] - 100; trail = False; count += 1
        if cl and can[i] and pos == 0 and count < 3:
            out.append(("entry", -1)); sl = c[i] + 100; trail = False; count += 1
        avg = ep_now.get(i, np.nan)
        if pos > 0 and not trail and h[i] >= avg + 200:
            sl, trail = avg, True
        if pos < 0 and not trail and l[i] <= avg - 200:
            sl, trail = avg, True
        store[i] = (sl, tpu if pos > 0 else tpl) if pos != 0 else None
        if eod[i] and pos != 0:
            out.append(("close", pos))
        return out

    def level(k):
        def fn(i, pos, ep, eb):
            ep_now[i] = ep
            if i == 0 or store[i - 1] is None or poscl[i - 1] != pos:
                return None
            v = store[i - 1][k]
            return None if np.isnan(v) else v
        return fn

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
