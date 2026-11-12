"""Independent check — 9/21 EMA EOD exit (6Cfdi5U9): 15-minute bars (24h synthetic, New York clock), one position (reversals), trade list only. The backtest range inputs are moved into the synthetic data (2015-02-01 .. 2015-06-30 UTC, passed
to both sides). EMA9 crossing over (under) EMA21 on a green (red) candle with the bar between 09:30 and 14:59 enters when not already that way (reversing the opposite side); the first bar from 15:15 on that follows a bar before 15:15 closes any open
position (close_all, next open). Margin and slippage off, 5% size on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "6Cfdi5U9"
T0 = int(pd.Timestamp("2015-02-01", tz="UTC").value // 10**6)
T1 = int(pd.Timestamp("2015-06-30", tz="UTC").value // 10**6)


def check():
    df = bars(12000, seed=474, freq="15min")
    t = df["time"].to_numpy()
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    hh, mm = ny.dt.hour.to_numpy(), ny.dt.minute.to_numpy()
    win = ((hh > 9) | ((hh == 9) & (mm >= 30))) & (hh < 15)
    eod = ((hh == 15) & (mm >= 15)) | (hh > 15)
    inr = (t >= T0) & (t <= T1)
    e9, e21 = np_ema(c, 9), np_ema(c, 21)
    with np.errstate(invalid="ignore"):
        bs = np_cross_over(e9, e21) & (c > o) & win & inr
        ss = np_cross_under(e9, e21) & (c < o) & win & inr

    def orders(i, pos):
        out = []
        eprev = eod[i - 1] if i > 0 else False
        if bs[i] and pos <= 0 and not eod[i]:
            out.append(("entry", 1))
        if ss[i] and pos >= 0 and not eod[i]:
            out.append(("entry", -1))
        if eod[i] and not eprev and pos != 0 and inr[i]:
            out += [("close", 1), ("close", -1)]
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params={"Backtest start": T0, "Backtest end": T1},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "default_qty_value": 5}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
