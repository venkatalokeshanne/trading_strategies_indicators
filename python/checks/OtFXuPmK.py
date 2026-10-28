"""Independent check — Auto-Logger MTF + Calendar (OtFXuPmK): daily bars, Start Year 2016 here (passed to both sides; bars begin 2015-01-01 UTC, so the 2016-01-01 00:00 New York start excludes earlier bars; New York is the exchange time zone). EMA9 crossing over EMA21 with close > EMA200 goes long,
the cross under with close < EMA200 goes short, both only inside the window, at the next open, reversing."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "OtFXuPmK"


def check():
    df = bars(9000, seed=24)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    f, s, r = np_ema(c, 9), np_ema(c, 21), np_ema(c, 200)
    t0 = pd.Timestamp(year=2016, month=1, day=1, tz="America/New_York").value // 1_000_000
    t1 = pd.Timestamp(year=2030, month=12, day=31, hour=23, minute=59, tz="America/New_York").value // 1_000_000
    t = df["time"].to_numpy()
    inr = (t >= t0) & (t <= t1)
    with np.errstate(invalid="ignore"):
        lg = np_cross_over(f, s) & (c > r)
        sh = np_cross_under(f, s) & (c < r)

    def orders(i, pos):
        out = []
        if inr[i] and lg[i]:
            out.append(("entry", 1))
        if inr[i] and sh[i]:
            out.append(("entry", -1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Start Year": 2016},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
