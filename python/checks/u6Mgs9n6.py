"""Independent check — 5 Min Liquidity Sweep Short (u6Mgs9n6): 5-min bars, day = 09:30 NY session. Short when the previous
bar was bullish and set the running day high, and this bar closes under the previous open while its high exceeds the previous
high; only when flat; stop = signal high, target = same distance below the close, bracket working from the next bar."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "u6Mgs9n6"


def check():
    df = bars(20000, seed=82, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    key = (ny - pd.Timedelta(minutes=570)).dt.date.to_numpy()
    dh = np.full(n, np.nan)                                # nan until the first day change (bar 0 has na change)
    for i in range(1, n):
        dh[i] = h[i] if key[i] != key[i - 1] else max(dh[i - 1], h[i]) if not np.isnan(dh[i - 1]) else np.nan
    sig = np.zeros(n, bool)
    for i in range(2, n):
        sig[i] = (c[i - 1] > o[i - 1]) and (h[i - 1] >= dh[i - 1]) and (c[i] < o[i - 1]) and (h[i] > h[i - 1])
    lvl = [(np.nan, np.nan)] * n
    cur = (np.nan, np.nan)
    after = []

    def orders(i, pos):
        nonlocal cur
        out = []
        if sig[i] and pos == 0 and (h[i] - c[i]) > 0:
            cur = (h[i], c[i] - (h[i] - c[i]))             # (stop, target)
            out.append(("entry", -1))
        after.append(cur)
        return out

    ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: after[i - 1][0] if i > 0 else None,
                   target=lambda i, pos, ep, eb: after[i - 1][1] if i > 0 else None)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
