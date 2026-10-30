"""Independent check — VWAP Mean Reversion + Session Filter (YnLk5B6z): 5-min New York bars, VWAP of hlc3.
Fade moves beyond VWAP +/- 1.5 ATR on weak volume (< SMA20) between 09:45 and 15:15, only when flat;
stop 1.5 ATR from the signal close, target = signal-bar VWAP, both working from the next bar."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_sma, np_vwap, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "YnLk5B6z"


def check():
    df = bars(20000, seed=76, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    sess = (m >= 9 * 60 + 45) & (m < 15 * 60 + 15)
    vw, atr = np_vwap(df, (h + l + c) / 3), np_atr(h, l, c, 14)
    weak = v < np_sma(v, 20)
    with np.errstate(invalid="ignore"):
        lsig = (c < vw - atr * 1.5) & weak & sess
        ssig = (c > vw + atr * 1.5) & weak & sess
    # bracket levels as last issued at or before each bar; issued only on signal bars that pass the flat test
    levels = {1: [], -1: []}
    cur = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}

    def orders2(i, pos):
        out = []
        if pos == 0:
            if lsig[i]:
                out.append(("entry", 1))
                cur[1] = (c[i] - atr[i] * 1.5, vw[i])
            if ssig[i]:
                out.append(("entry", -1))
                cur[-1] = (c[i] + atr[i] * 1.5, vw[i])
        for d in (1, -1):
            levels[d].append(cur[d])
        return out

    def level(k):
        return lambda i, pos, ep, eb: levels[pos][i - 1][k] if i > 0 else None

    ref = simulate(o, h, l, c, orders2, stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
