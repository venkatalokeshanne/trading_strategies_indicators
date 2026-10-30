"""Independent check — 9/20 EMA Retest (WhQK3Xhy): 15-min bars. A cross of EMA9 over EMA20 arms longs (and disarms shorts), a cross of EMA20 over EMA9 arms shorts. While armed, EMA9 > EMA20 (< for shorts), a bar whose low touches either EMA (high for shorts),
a bullish (bearish) candle, inside 09:00-16:00 India time, enters when flat; stop = candle low (high), target = entry +/- 3 x risk, fixed at the signal bar."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "WhQK3Xhy"


def check():
    df = bars(16000, seed=84, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ist = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Asia/Kolkata")
    mins = (ist.dt.hour * 60 + ist.dt.minute).to_numpy()
    sess = (mins >= 540) & (mins < 960)
    e9, e20 = np_ema(c, 9), np_ema(c, 20)
    bc, sc = np_cross_over(e9, e20), np_cross_over(e20, e9)
    st = dict(b=False, s=False)
    lvl = {}

    def orders(i, pos):
        out = []
        if bc[i]:
            st["b"], st["s"] = True, False
        if sc[i]:
            st["s"], st["b"] = True, False
        with np.errstate(invalid="ignore"):
            bo = st["b"] and e9[i] > e20[i] and (l[i] <= e9[i] or l[i] <= e20[i]) and c[i] > o[i] and sess[i]
            so = st["s"] and e20[i] > e9[i] and (h[i] >= e9[i] or h[i] >= e20[i]) and c[i] < o[i] and sess[i]
        if bo and pos == 0:
            out.append(("entry", 1))
            lvl[1] = (l[i], c[i] + (c[i] - l[i]) * 3)
        if so and pos == 0:
            out.append(("entry", -1))
            lvl[-1] = (h[i], c[i] - (h[i] - c[i]) * 3)
        return out

    def stop(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][0]

    def target(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][1]

    ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
