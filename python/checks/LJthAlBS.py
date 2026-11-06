"""Independent check — Options Momentum Bias v2 (LJthAlBS): 15-min continuous bars. Session 09:30-16:00 New York (bar start). VWAP of close (09:30-NY reset). Bull: close > VWAP, EMA9 > EMA20, close > EMA50, volume > 1.2 x SMA20, lowest low of 3 bars <= EMA9, close > previous high, bullish, EMA9 rising; cooldown 5 bars from the last same-side signal;
signal when not already long (not short for bears), entering at the next open (reversing). Both exits are rebuilt every bar from the position average price at script time (stop 1 ATR14, target 1.5 ATR14; na while flat), each applying to its own direction from the next bar (also after a reversal). A long closes (next open) when close < VWAP, a short when close > VWAP."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_sma, np_vwap, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "LJthAlBS"


def check():
    df = bars(14000, seed=310, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    sess = (mins >= 570) & (mins < 960)
    vw = np_vwap(df, c)
    e9, e20, e50 = np_ema(c, 9), np_ema(c, 20), np_ema(c, 50)
    atr = np_atr(h, l, c, 14)
    ll3 = pd.Series(l).rolling(3).min().to_numpy()
    hh3 = pd.Series(h).rolling(3).max().to_numpy()
    h1, l1, e91 = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]], np.r_[np.nan, e9[:-1]]
    with np.errstate(invalid="ignore"):
        va = v > np_sma(v, 20) * 1.2
        bu = sess & (c > vw) & (e9 > e20) & (c > e50) & va & (ll3 <= e9) & (c > h1) & (c > o) & (e9 > e91)
        be = sess & (c < vw) & (e9 < e20) & (c < e50) & va & (hh3 >= e9) & (c < l1) & (c < o) & (e9 < e91)
    s = dict(lb=None, ls=None)
    tmp, lv = {}, {}

    def orders(i, pos):
        out = []
        cb = s["lb"] is None or i - s["lb"] > 5
        cs = s["ls"] is None or i - s["ls"] > 5
        bsg = bu[i] and cb and pos <= 0
        ssg = be[i] and cs and pos >= 0
        if bsg:
            s["lb"] = i
        if ssg:
            s["ls"] = i
        if bsg:
            out.append(("entry", 1))
        if ssg:
            out.append(("entry", -1))
        ep = tmp.get(i) if pos != 0 else None
        lv[i] = None if ep is None else (ep, atr[i])
        with np.errstate(invalid="ignore"):
            if pos > 0 and c[i] < vw[i]:
                out.append(("close", 1))
            if pos < 0 and c[i] > vw[i]:
                out.append(("close", -1))
        return out

    def stop(i, pos, ep, eb):
        tmp[i] = ep
        p = lv.get(i - 1) if i > 0 else None
        if p is None or np.isnan(p[1]):
            return None
        return p[0] - p[1] if pos > 0 else p[0] + p[1]

    def target(i, pos, ep, eb):
        p = lv.get(i - 1) if i > 0 else None
        if p is None or np.isnan(p[1]):
            return None
        return p[0] + 1.5 * p[1] if pos > 0 else p[0] - 1.5 * p[1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
