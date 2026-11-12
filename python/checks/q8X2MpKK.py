"""Independent check — Micro Rejection Scalping (q8X2MpKK): 5-minute bars (24h synthetic), short only, one position, trade list only. Short signal: EMA9 crosses under EMA21, New York hour in [7, 11), at least 12 bars since the last signal
(the counter starts at bar 0), flat. Stop = high + 0.8 ATR14 (ATR taken as 1.0 while na), distance = max(stop - close, 0.1 ATR); limit = close - max(2 ATR, that distance); both fixed at the signal bar and working from the fill bar. Margin and
slippage off, 5% size on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "q8X2MpKK"


def check():
    df = bars(25000, seed=838, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    hr = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York").dt.hour.to_numpy()
    cu = np_cross_under(np_ema(c, 9), np_ema(c, 21))
    atr = np_atr(h, l, c, 14)
    S = dict(last=0, sl=np.nan, tp=np.nan)

    def orders(i, pos):
        a = 1.0 if np.isnan(atr[i]) else atr[i]
        if cu[i] and 7 <= hr[i] < 11 and (i - S["last"]) >= 12 and pos == 0:
            sl = h[i] + a * 0.8
            dist = max(sl - c[i], a * 0.1)
            S["sl"], S["tp"] = sl, c[i] - max(a * 2.0, dist)
            S["last"] = i
            return [("entry", -1)]
        return []

    def stop(i, pos, ep, eb):
        return S["sl"]

    def target(i, pos, ep, eb):
        return S["tp"]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "default_qty_value": 5}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
