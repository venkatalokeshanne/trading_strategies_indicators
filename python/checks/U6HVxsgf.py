"""Independent check — RSI Strategy with TP and SL (U6HVxsgf): 5-min New York bars. RSI(50) crossing over 30 buys, under 38 sells short, but only when the
original's (quirky) hours expression holds: (hour >= 10 and minute >= 30) or (hour <= 14 and minute <= 30). Absolute +100 target / -250 stop from the
signal close for longs (mirrored for shorts), placed with the entry (works from the fill bar); opposite signals reverse."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "U6HVxsgf"


def check():
    df = bars(30000, seed=133, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    hr, mi = ny.dt.hour.to_numpy(), ny.dt.minute.to_numpy()
    rsi = np_rsi(c, 50)
    with np.errstate(invalid="ignore"):
        lc, sc = np_cross_over(rsi, 30), np_cross_under(rsi, 38)
    hours = ((hr >= 10) & (mi >= 30)) | ((hr <= 14) & (mi <= 30))
    ok_bar = ~np.isnan(rsi) & hours
    cur = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}
    hist = []

    def orders(i, pos):
        out = []
        if ok_bar[i] and lc[i]:
            out.append(("entry", 1)); cur[1] = (c[i] - 250.0, c[i] + 100.0)
        if ok_bar[i] and sc[i]:
            out.append(("entry", -1)); cur[-1] = (c[i] + 250.0, c[i] - 100.0)
        hist.append(dict(cur))
        return out

    ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: hist[i - 1][pos][0] if i > 0 else None,
                   target=lambda i, pos, ep, eb: hist[i - 1][pos][1] if i > 0 else None)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
