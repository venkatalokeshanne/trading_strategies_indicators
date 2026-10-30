"""Independent check — Option-Point (PbpHZFY8): 15-min continuous bars, short only. EMA9 crossing under EMA21 while both (EMA - EMA[3])/3 slopes are below -0.05 / -0.02 and the bar starts inside the 0920-1520 NSE session window sells when flat (next open); EMA9 crossing over
EMA21 closes a short; the first bar after the session ends closes it too. Session = 0920-1520 in the symbol's exchange time zone (New York)."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "PbpHZFY8"
SLB = 3
A, B = 560, 920


def check():
    df = bars(14000, seed=360, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    ins = (mins >= A) & (mins < B)
    f, s = np_ema(c, 9), np_ema(c, 21)
    fs = (f - np.r_[[np.nan] * SLB, f[:-SLB]]) / SLB
    ss = (s - np.r_[[np.nan] * SLB, s[:-SLB]]) / SLB
    with np.errstate(invalid="ignore"):
        sell = np_cross_under(f, s) & (fs < -0.05) & (ss < -0.02) & ins
        ex = np_cross_over(f, s)
    prev = np.r_[False, ins[:-1]]

    def orders(i, pos):
        out = []
        if sell[i] and pos == 0:
            out.append(("entry", -1))
        if ex[i] and pos < 0:
            out.append(("close", -1))
        if (not ins[i]) and prev[i] and pos < 0:
            out.append(("close", -1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
