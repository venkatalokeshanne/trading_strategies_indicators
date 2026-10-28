"""Independent check — VWAP ORB Pullback (75epRRh2): 5-min New York bars. Opening range = bars whose start
is in [09:30, 09:45] (the 09:30 bar is cleared again by the same-bar `ta.change(time("D"))` reset, as in
Pine's statement order); long/short on a close beyond the range after a VWAP+EMA9 pullback; bracket
ATR / 1.5 ATR issued at the signal bar, working from the next bar."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_vwap, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "75epRRh2"


def check():
    df = bars(20000, seed=75, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    key = (ny - pd.Timedelta(minutes=570)).dt.date.to_numpy()
    in_or = (m >= 570) & (m <= 585)
    after_or = m > 585                                   # time > or_end_time (today's 09:45), bars are on one calendar day
    vw, atr, e9 = np_vwap(df, c), np_atr(h, l, c, 14), np_ema(c, 9)
    orh, orl = np.full(n, np.nan), np.full(n, np.nan)
    ch, cl = np.nan, np.nan
    for i in range(n):
        if in_or[i]:
            ch = h[i] if np.isnan(ch) else max(ch, h[i])
            cl = l[i] if np.isnan(cl) else min(cl, l[i])
        if i > 0 and key[i] != key[i - 1]:               # ta.change(time("D")) != 0 (na on bar 0 -> false)
            ch = cl = np.nan
        orh[i], orl[i] = ch, cl
    with np.errstate(invalid="ignore"):
        lgo = (c > orh) & (c > vw) & (c > e9) & (l <= vw) & after_or
        sgo = (c < orl) & (c < vw) & (c < e9) & (h >= vw) & after_or
    lv = {1: [], -1: []}
    cur = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}
    for j in range(n):
        if lgo[j]:
            cur[1] = (c[j] - atr[j], c[j] + atr[j] * 1.5)
        if sgo[j]:
            cur[-1] = (c[j] + atr[j], c[j] - atr[j] * 1.5)
        lv[1].append(cur[1]); lv[-1].append(cur[-1])

    def level(k):
        return lambda i, pos, ep, eb: lv[pos][i - 1][k] if i > 0 else None

    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if lgo[i] else []) + ([("entry", -1)] if sgo[i] else []),
                   stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
