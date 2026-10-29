"""Independent check — SPY VWAP + Squeeze Breakout (HNql4p3J): 5-min bars on a New York clock.
ta.vwap(close): source = close, reset at the 09:30 New York session start.
Squeeze fires when it was ON on the previous bar and is OFF now (Bollinger vs Keltner, population stdev)."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_sma, np_tr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "HNql4p3J"


def roll_std(x, n):                       # population stdev, na until n bars
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = np.std(x[i - n + 1:i + 1])
    return out


def check():
    df = bars(6000, seed=72, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    day = (ny.dt.tz_localize(None) - pd.Timedelta(minutes=9 * 60 + 30)).dt.date.to_numpy()
    pv, vv, vw = 0.0, 0.0, np.empty(len(c))
    for i in range(len(c)):
        if i == 0 or day[i] != day[i - 1]:
            pv = vv = 0.0
        pv, vv = pv + c[i] * v[i], vv + v[i]
        vw[i] = pv / vv
    basis = np_sma(c, 20)
    d = 2.0 * roll_std(c, 20)
    up, lo = basis + d, basis - d
    rma_ = np_sma(np_tr(h, l, c, True), 20)
    ukc, lkc = np_sma(c, 20) + rma_ * 1.5, np_sma(c, 20) - rma_ * 1.5
    with np.errstate(invalid="ignore"):
        on = (lo > lkc) & (up < ukc)
        off = (lo < lkc) | (up > ukc)
    fired = off & np.r_[False, on[:-1]]
    with np.errstate(invalid="ignore"):
        lc = (c > vw) & fired & (c > o)
        sc = (c < vw) & fired & (c < o)
        lx, sx = c < vw, c > vw

    def orders(i, pos):
        out = []
        if lc[i]:
            out.append(("entry", 1))
        if sc[i]:
            out.append(("entry", -1))
        if pos > 0 and lx[i]:                  # position_size read at bar close, before this bar's entries fill
            out.append(("close", 1))
        if pos < 0 and sx[i]:
            out.append(("close", -1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock")
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 20, f"{detail} (need >20 trades, got {len(ref)})"
