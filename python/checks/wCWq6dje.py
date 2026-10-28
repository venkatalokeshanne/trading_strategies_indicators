"""Independent check — Wed to Thu 9:20 Nifty (wCWq6dje): 5-min bars on a mean-reverting index around 20000 (so the 100-point stop is meaningful). Times in Asia/Kolkata (09:15 bar = 03:45 UTC). On each week (pinelib's session-aligned
week: ISO week of New York time minus 09:30) the Tuesday 09:15 close and the Wednesday 09:15 close are stored and rolled to 'previous' at the next week start. Wednesday 09:15: reference = previous Wednesday price, else previous Tuesday
price; close above buys, below sells short (fills next open). Stop 100 points from the average price issued while a position is open at a close (works from the next bar); any non-Wednesday bar from 15:15 IST closes an open
position at the next open. Margin 100 % is kept."""
import numpy as np
import pandas as pd

from indep import compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "wCWq6dje"


def ou_bars(n, seed, mu, theta, sigma, freq="5min"):
    rng = np.random.default_rng(seed)
    x = np.empty(n)
    x[0] = mu
    for i in range(1, n):
        x[i] = x[i - 1] + theta * (mu - x[i - 1]) + sigma * rng.normal()
    open_ = np.r_[x[0], x[:-1]] + rng.normal(0, sigma / 8, n)
    high = np.maximum(open_, x) + np.abs(rng.normal(0, sigma / 2, n))
    low = np.minimum(open_, x) - np.abs(rng.normal(0, sigma / 2, n))
    t = pd.date_range("2015-01-01", periods=n, freq=freq, tz="UTC").as_unit("ms").asi8
    return pd.DataFrame({"time": t, "open": open_, "high": high, "low": low, "close": x, "volume": rng.integers(1000, 100000, n).astype(float)})


def check():
    df = ou_bars(60000, 263, 20000.0, 0.002, 25.0)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    t = pd.to_datetime(df["time"], unit="ms", utc=True)
    ist = t.dt.tz_convert("Asia/Kolkata")
    hr, mi = ist.dt.hour.to_numpy(), ist.dt.minute.to_numpy()
    dow = ((ist.dt.dayofweek.to_numpy() + 1) % 7) + 1                    # Pine numbering, Sunday = 1
    iso = (t.dt.tz_convert("America/New_York") - pd.Timedelta(minutes=570)).dt.isocalendar()
    wk = (iso["year"].astype(int) * 100 + iso["week"].astype(int)).to_numpy()
    t920 = (hr == 9) & (mi == 15)
    texit = (dow != 4) & (hr == 15) & (mi >= 15)
    ptue = pwed = ctue = cwed = ref = np.nan

    def orders(i, pos):
        nonlocal ptue, pwed, ctue, cwed, ref
        if i > 0 and wk[i] != wk[i - 1]:
            ptue, pwed, ctue, cwed, ref = ctue, cwed, np.nan, np.nan, np.nan
        out = []
        if dow[i] == 3 and t920[i]:
            ctue = c[i]
        if dow[i] == 4 and t920[i]:
            ref = ptue if np.isnan(pwed) else pwed
            if not np.isnan(ref):
                if c[i] > ref:
                    out.append(("entry", 1))
                if c[i] < ref:
                    out.append(("entry", -1))
            cwed = c[i]
        if pos != 0 and texit[i]:
            out.append(("close", pos))
        return out

    ref_trades = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: None if eb >= i else ep - pos * 100.0)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref_trades)
    return ok and len(ref_trades) > 10, f"{detail} (need >10 trades, got {len(ref_trades)})"
