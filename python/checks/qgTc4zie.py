"""Independent check — KAMA by MKB (qgTc4zie): daily bars, long only. Efficiency ratio = |c - c[21]| / sum of the last 21 |c - c[1]| (na until 21 bars of changes exist, 0 if the sum is 0); smooth = (ER*(0.666-0.0645)+0.0645)^2;
kama = nz(kama[1]) + smooth*(c - nz(kama[1])) (so it restarts from 0 on the first non-na bar); upper = kama + 0.5 * population stdev(20). Close crossing over upper while flat enters; crossing under kama while long closes at
the next open. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "qgTc4zie"


def check():
    df = bars(6000, seed=233)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    d1 = np.abs(c - np.r_[np.nan, c[:-1]])
    sig = np.abs(c - np.r_[np.full(21, np.nan), c[:-21]])
    noise = pd.Series(d1).rolling(21).sum().to_numpy()                 # NaN until 21 non-na changes
    with np.errstate(invalid="ignore", divide="ignore"):
        er = np.where(noise != 0, sig / noise, 0.0)                   # NaN != 0 -> NaN ratio
    er = np.where(np.isnan(noise), np.nan, er)
    smooth = (er * (0.666 - 0.0645) + 0.0645) ** 2
    kama = np.empty(n)
    prev = 0.0
    for i in range(n):
        p = 0.0 if np.isnan(prev) else prev
        kama[i] = p + smooth[i] * (c[i] - p)
        prev = kama[i]
    sd = pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    up = kama + 0.5 * sd
    bs, ss = np_cross_over(c, up), np_cross_under(c, kama)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if bs[i] and pos == 0 else []) + ([("close", 1)] if ss[i] and pos > 0 else []))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
