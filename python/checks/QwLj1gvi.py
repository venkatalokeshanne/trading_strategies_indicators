"""Independent check — BankNifty 15m Clear TP/SL (QwLj1gvi): 15-min New York bars. 09:30-12:15 window (minutes of day 570..735 inclusive, bar start), ADX14 >= 12, EMA20/50 trend with close beyond the previous bar's
high / low enters when pos <= 0 / >= 0 (reversing); SL = close -/+ 1.2 ATR and TP = 2 R are var levels checked on later closes (a close at / beyond a level closes at the next open; the long block is checked with the latest
long levels, the short block with the latest short levels)."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_adx, np_atr, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "QwLj1gvi"


def check():
    df = bars(40000, seed=234, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    win = (m >= 570) & (m <= 735)
    f, s, atr, adx = np_ema(c, 20), np_ema(c, 50), np_atr(h, l, c, 14), np_adx(h, l, c, 14)
    h1, l1 = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    with np.errstate(invalid="ignore"):
        lg = win & ~(adx < 12) & (f > s) & (c > f) & (c > h1)
        sg = win & ~(adx < 12) & (f < s) & (c < f) & (c < l1)
    lv = dict(lsl=np.nan, ltp=np.nan, ssl=np.nan, stp=np.nan)

    def orders(i, pos):
        out = []
        if lg[i] and pos <= 0:
            out.append(("entry", 1)); lv["lsl"], lv["ltp"] = c[i] - atr[i] * 1.2, c[i] + atr[i] * 1.2 * 2.0
        if sg[i] and pos >= 0:
            out.append(("entry", -1)); lv["ssl"], lv["stp"] = c[i] + atr[i] * 1.2, c[i] - atr[i] * 1.2 * 2.0
        if pos > 0 and (c[i] <= lv["lsl"] or c[i] >= lv["ltp"]):
            out.append(("close", 1))
        if pos < 0 and (c[i] >= lv["ssl"] or c[i] <= lv["stp"]):
            out.append(("close", -1))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="15"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
