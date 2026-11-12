"""Independent check — Gold Breakout PRO (PU4lrqHR): 5-min New York bars. Close beyond the previous bar's 20-bar high/low in the direction of the daily
close vs its daily EMA50 (daily bars from plain pandas, lookahead off: last chart bar of the day = that day, earlier bars = previous day) with a
wide candle (range > 20 % of the 20-bar range). Exits unconditional: bar i works with bar i-1's stop = 20-bar low (long) / high (short) and target =
avg + (avg - stop) * 1.5 where avg is the position's average price at the previous close (na while flat -> only the stop works)."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, np_periods, np_security_lookahead_off, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "PU4lrqHR"


def roll(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


def check():
    df = bars(30000, seed=126, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    pid, last_of = np_periods(df, 1440)
    dc = pd.Series(c).groupby(pid).last().to_numpy()
    d_close = np_security_lookahead_off(dc, pid, last_of)
    d_ema = np_security_lookahead_off(np_ema(dc, 50), pid, last_of)
    hh, ll = roll(h, 20, np.max), roll(l, 20, np.min)
    hh1, ll1 = np.r_[np.nan, hh[:-1]], np.r_[np.nan, ll[:-1]]
    with np.errstate(invalid="ignore"):
        strong = (h - l) > (hh - ll) * 0.2
        lg = (c > hh1) & (c > o) & strong & (d_close > d_ema)
        sg = (c < ll1) & (c < o) & strong & (d_close < d_ema)
    ep_now, avg_close = {}, np.full(n, np.nan)

    def orders(i, pos):
        avg_close[i] = ep_now.get(i, np.nan) if pos != 0 else np.nan
        return ([("entry", 1)] if lg[i] else []) + ([("entry", -1)] if sg[i] else [])

    def stop(i, pos, ep, eb):
        ep_now[i] = ep
        if i == 0:
            return None
        return ll[i - 1] if pos > 0 else hh[i - 1]

    def target(i, pos, ep, eb):
        if i == 0 or np.isnan(avg_close[i - 1]):
            return None
        a = avg_close[i - 1]
        return a + (a - ll[i - 1]) * 1.5 if pos > 0 else a - (hh[i - 1] - a) * 1.5

    ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
