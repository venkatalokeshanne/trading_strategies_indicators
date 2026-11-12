"""Independent check — Fund-Grade Daytrade System (BRsHHMWi): 5-min bars (24h synthetic) on an extended-hours chart (trading day starts 04:00 New York), one position, trade list only. Pre-market high / low = running extremes of the
04:00-09:30 bars, reset at the first bar of each trading day. During 09:30-16:00 a close above the pre-market high (below the low) enters, unless: the bar is in the first window (bar time <= 09:35 on that calendar date - this includes ALL
earlier bars of the date), the side is blocked (an early wick through the range that closes back inside sets the block, which clears at a new day and at the first bar outside the first window), or the anti-chop filter fails
(ADX14 >= 18 and 100 x (2 x stdev20) / SMA20 > 0.5). Stop = close -/+ 1.5 ATR14, target 2R, both fixed at the signal bar (re-issued on every signal, also when the side is already open). Margin and slippage off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_dmi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "BRsHHMWi"


def check():
    df = bars(25000, seed=777, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    tday = (ny.dt.tz_localize(None) - pd.Timedelta(minutes=240)).dt.date.to_numpy()
    in_pm = (m >= 240) & (m < 570)
    in_reg = (m >= 570) & (m < 960)
    first = (m - 570) <= 5
    _, _, adx = np_dmi(h, l, c, 14)
    basis = np_sma(c, 20)
    dev = pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    with np.errstate(invalid="ignore"):
        ok_chop = (adx >= 18) & ((100 * (2 * dev) / basis) > 0.5)
    atr = np_atr(h, l, c, 14)
    S = dict(H=np.nan, L=np.nan, bl=False, bs=False)
    lv = {1: None, -1: None}

    def orders(i, pos):
        out = []
        new_day = i > 0 and tday[i] != tday[i - 1]
        if new_day:
            S["H"] = S["L"] = np.nan
        if in_pm[i]:
            S["H"] = h[i] if np.isnan(S["H"]) else max(S["H"], h[i])
            S["L"] = l[i] if np.isnan(S["L"]) else min(S["L"], l[i])
        lb = in_reg[i] and not np.isnan(S["H"]) and c[i] > S["H"]
        sb = in_reg[i] and not np.isnan(S["L"]) and c[i] < S["L"]
        eu = first[i] and not np.isnan(S["H"]) and h[i] > S["H"]
        ed = first[i] and not np.isnan(S["L"]) and l[i] < S["L"]
        fu = eu and c[i] < S["H"]
        fd = ed and c[i] > S["L"]
        if new_day:
            S["bl"] = S["bs"] = False
        if fu:
            S["bl"] = True
        if fd:
            S["bs"] = True
        if not first[i]:
            S["bl"] = S["bs"] = False
        allow_l = (not S["bl"]) and not first[i]
        allow_s = (not S["bs"]) and not first[i]
        with np.errstate(invalid="ignore"):
            chop = bool(ok_chop[i])
        if lb and chop and allow_l:
            sl = c[i] - atr[i] * 1.5
            lv[1] = (sl, c[i] + (c[i] - sl) * 2.0)
            out.append(("entry", 1))
        if sb and chop and allow_s:
            sl = c[i] + atr[i] * 1.5
            lv[-1] = (sl, c[i] - (sl - c[i]) * 2.0)
            out.append(("entry", -1))
        return out

    def stop(i, pos, ep, eb):
        return lv[pos][0] if lv[pos] else None

    def target(i, pos, ep, eb):
        return lv[pos][1] if lv[pos] else None

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9, extended_hours=True)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "default_qty_value": 5}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
