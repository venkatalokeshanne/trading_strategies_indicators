"""Independent check — Smart Scalping PRO (jKcFbQoy): 5-min New York bars. Long: close > EMA50 > EMA200 with EMA50 above its value 5 bars ago, RSI3 crossing over 20, ADX(5) > 30, ATR14 > SMA20(ATR14), bar start in 08:00-12:00 or
13:00-17:00 NY; short mirrored (RSI3 crossing under 80). Signal bar issues entry + exit (stop = close -/+ 1.2 ATR, limit = 1.5 R), so the bracket works from the fill bar; a repeat signal on the open side replaces the
levels. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_adx, np_atr, np_cross_over, np_cross_under, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "jKcFbQoy"


def check():
    df = bars(60000, seed=235, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    sess = ((m >= 480) & (m < 720)) | ((m >= 780) & (m < 1020))
    e50, e200 = np_ema(c, 50), np_ema(c, 200)
    e5 = np.r_[np.full(5, np.nan), e50[:-5]]
    rsi, adx, atr = np_rsi(c, 3), np_adx(h, l, c, 5), np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        vol = atr > np_sma(atr, 20)
        lc = (c > e50) & (e50 > e200) & (e50 - e5 > 0) & np_cross_over(rsi, 20) & (adx > 30) & sess & vol
        sc = (c < e50) & (e50 < e200) & (e50 - e5 < 0) & np_cross_under(rsi, 80) & (adx > 30) & sess & vol
    lvl = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}

    def orders(i, pos):
        out = []
        if lc[i]:
            s = c[i] - atr[i] * 1.2
            out.append(("entry", 1)); lvl[1] = (s, c[i] + (c[i] - s) * 1.5)
        if sc[i]:
            s = c[i] + atr[i] * 1.2
            out.append(("entry", -1)); lvl[-1] = (s, c[i] - (s - c[i]) * 1.5)
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: lvl[pos][0], target=lambda i, pos, ep, eb: lvl[pos][1])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
