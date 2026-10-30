"""Independent check — Night Breakout 21:30 WIB (dW9UeMTL): 15-min bars. Entry only on the bar starting 21:15 Asia/Jakarta (14:15 UTC): EMA50 > EMA200 and close > EMA50, two green candles, low and previous low above EMA200 (EMA200[1]) -> long when flat
(mirror short). Stop = 20-bar lowest low (highest high), or 50 points (500 pips x 0.1) from the close when further; target 1:1 (close +/- the stop distance). Entry + exit on the signal bar (bracket works from the fill bar); no order when
the distance is 0. A position whose entry bar is 5 days (432000000 ms) or more behind the current bar is closed at the next open. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "dW9UeMTL"


def check():
    df = bars(60000, seed=312, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    t = df["time"].to_numpy()
    n = len(c)
    jk = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Asia/Jakarta")
    et = ((jk.dt.hour == 21) & (jk.dt.minute == 15)).to_numpy()
    e50, e200 = np_ema(c, 50), np_ema(c, 200)
    c1, o1, l1, h1, e1 = (np.r_[np.nan, x[:-1]] for x in (c, o, l, h, e200))
    rl = pd.Series(l).rolling(20).min().to_numpy()
    rh = pd.Series(h).rolling(20).max().to_numpy()
    with np.errstate(invalid="ignore"):
        lc = et & (e50 > e200) & (c > e50) & (c > o) & (c1 > o1) & (l > e200) & (l1 > e1)
        sc = et & (e50 < e200) & (c < e50) & (c < o) & (c1 < o1) & (h < e200) & (h1 < e1)
    lvl = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}
    eb = [None]

    def orders(i, pos):
        out = []
        with np.errstate(invalid="ignore"):
            if lc[i] and pos == 0:
                sl = c[i] - 50.0 if (c[i] - rl[i]) > 50.0 else rl[i]
                if c[i] - sl > 0:
                    out.append(("entry", 1)); lvl[1] = (sl, c[i] + (c[i] - sl)); eb[0] = i + 1
            if sc[i] and pos == 0:
                sl = c[i] + 50.0 if (rh[i] - c[i]) > 50.0 else rh[i]
                if sl - c[i] > 0:
                    out.append(("entry", -1)); lvl[-1] = (sl, c[i] - (sl - c[i])); eb[0] = i + 1
        if pos != 0 and eb[0] is not None and t[i] - t[eb[0]] >= 432000000:
            out.append(("close", pos))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb_: lvl[pos][0], target=lambda i, pos, ep, eb_: lvl[pos][1])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
