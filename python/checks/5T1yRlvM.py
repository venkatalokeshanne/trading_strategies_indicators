"""Independent check — PRO Scalping EMA50 + RSI3 + ADX5 (5T1yRlvM): 5-min New York bars. Long: close > EMA50 with EMA50 > its value 5 bars ago, RSI3 crossing over 20, ADX(5) > 30, body > 60 % of the range, bar start in
08:00-12:00 or 13:00-17:00 NY; short mirrored (RSI3 crossing under 80). Signal bar issues entry + exit (stop = bar low / high, limit = close +/- 1.5 risk), so the bracket works from the fill bar; a repeat signal on the
open side re-issues (replaces) the levels. The sim receives levels per direction set at the signal's close."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_adx, np_cross_over, np_cross_under, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "5T1yRlvM"


def check():
    df = bars(60000, seed=214, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    sess = ((m >= 480) & (m < 720)) | ((m >= 780) & (m < 1020))
    e = np_ema(c, 50)
    e5 = np.r_[np.full(5, np.nan), e[:-5]]
    rsi, adx = np_rsi(c, 3), np_adx(h, l, c, 5)
    strong = np.abs(c - o) > (h - l) * 0.6
    with np.errstate(invalid="ignore"):
        lc = (c > e) & (e - e5 > 0) & np_cross_over(rsi, 20) & (adx > 30) & strong & sess
        sc = (c < e) & (e - e5 < 0) & np_cross_under(rsi, 80) & (adx > 30) & strong & sess
    lvl = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}

    def orders(i, pos):
        out = []
        if lc[i]:
            out.append(("entry", 1)); lvl[1] = (l[i], c[i] + (c[i] - l[i]) * 1.5)
        if sc[i]:
            out.append(("entry", -1)); lvl[-1] = (h[i], c[i] - (h[i] - c[i]) * 1.5)
        return out

    def level(k):
        return lambda i, pos, ep, eb: lvl[pos][k]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
