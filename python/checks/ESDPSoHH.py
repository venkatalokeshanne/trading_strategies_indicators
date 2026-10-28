"""Independent check — EMA Cross + 1H Bias + VWAP SL/TP (ESDPSoHH): 5-min New York bars. Hourly bars are built with plain
pandas (60-minute blocks counted from the 09:30 session start); request.security with lookahead off shows an hour's close/EMA20
on the LAST 5-min bar of that hour and the previous hour's value on the earlier bars. EMA10/20 cross, close vs VWAP(close), and
a VWAP stop with 1R target issued at the signal bar."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, np_vwap, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "ESDPSoHH"


def check():
    df = bars(20000, seed=92, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    day = (ny - pd.Timedelta(minutes=570)).dt.date.to_numpy()
    slot = (((ny.dt.hour * 60 + ny.dt.minute - 570) % 1440) // 60).to_numpy()
    key = np.array([f"{d}-{s}" for d, s in zip(day, slot)])
    starts = np.r_[True, key[1:] != key[:-1]]
    pid = np.cumsum(starts) - 1                               # hour index of each chart bar
    last_of = np.r_[key[1:] != key[:-1], True]                # last chart bar of its hour
    hc = pd.Series(c).groupby(pid).last().to_numpy()          # final close of each hour
    he = np_ema(hc, 20)                                       # EMA of hourly closes
    htf_close, htf_ema = np.full(n, np.nan), np.full(n, np.nan)
    for j in range(n):
        p = pid[j] if last_of[j] else pid[j] - 1              # lookahead off: completed hour only
        if p >= 0:
            htf_close[j], htf_ema[j] = hc[p], he[p]
    f, s, vw = np_ema(c, 10), np_ema(c, 20), np_vwap(df, c)
    with np.errstate(invalid="ignore"):
        lg = np_cross_over(f, s) & (htf_close > htf_ema) & (c > vw)
        sg = np_cross_under(f, s) & (htf_close < htf_ema) & (c < vw)
    lv = {1: [], -1: []}
    cur = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}
    for j in range(n):
        if lg[j]:
            cur[1] = (vw[j], c[j] + (c[j] - vw[j]))
        if sg[j]:
            cur[-1] = (vw[j], c[j] - (vw[j] - c[j]))
        lv[1].append(cur[1]); lv[-1].append(cur[-1])

    def level(k):
        return lambda i, pos, ep, eb: lv[pos][i - 1][k] if i > 0 else None

    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if lg[i] else []) + ([("entry", -1)] if sg[i] else []),
                   stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
