"""Independent check — ES EMA Pullback System (KIXi6RHP): 5-min New York bars, short only. EMA 9<21<50, high back to EMA9 and a down
candle, bar start inside 09:30-11:30 or 13:30-16:00 (end exclusive). Exit re-issued every bar: stop = close + 1.6 ATR,
target = close - 3.2 ATR; bar i works with bar i-1's levels (also on the fill bar)."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "KIXi6RHP"


def check():
    df = bars(20000, seed=95, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    sess = ((m >= 570) & (m < 690)) | ((m >= 810) & (m < 960))
    e9, e21, e50, atr = np_ema(c, 9), np_ema(c, 21), np_ema(c, 50), np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        sig = (e9 < e21) & (e21 < e50) & (h >= e9) & (c < o) & sess
    ref = simulate(o, h, l, c, lambda i, pos: [("entry", -1)] if sig[i] else [],
                   stop=lambda i, pos, ep, eb: c[i - 1] + atr[i - 1] * 1.6 if i > 0 else None,
                   target=lambda i, pos, ep, eb: c[i - 1] - atr[i - 1] * 3.2 if i > 0 else None)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
