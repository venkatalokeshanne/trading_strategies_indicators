"""Independent check — NQ EMA VWAP (0mSobwAz): hourly bars, VWAP of close reset each UTC day."""
import numpy as np
import pandas as pd
from indep import bars, compare, np_ema, run_conversion, simulate


def check():
    df = bars(3000, seed=24, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    day = pd.to_datetime(df["time"], unit="ms", utc=True).dt.date
    vwap = ((df["close"] * df["volume"]).groupby(day).cumsum() / df["volume"].groupby(day).cumsum()).to_numpy()
    e20, e50 = np_ema(c, 20), np_ema(c, 50)
    p20, p50 = np.r_[np.nan, e20[:-1]], np.r_[np.nan, e50[:-1]]
    lc = (e20 > e50) & (p20 <= p50) & (c > vwap)
    sc = (e20 < e50) & (p20 >= p50) & (c < vwap)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if lc[i] else []) + ([("entry", -1)] if sc[i] else []))
    return compare(run_conversion("0mSobwAz", df, tf="60"), ref)
