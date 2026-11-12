"""Independent check — Clean VWAP ZL Scalper (qPXMv5X4): 15-min continuous bars, orders at the signal close (process_orders_on_close). Zero-lag EMA34 = EMA34(close + (close - close[16])); VWAP(hlc3, 09:30-NY reset); dev = population stdev(hlc3, 50). Bull: close > ZL and VWAP, a pullback (low <= VWAP, VWAP - dev, or ZL), a rejection candle
(lower wick > body and upper wick <= 1.2 body, or just close > open) and a confirm candle (close > open and close >= previous open), and the last signal was not already long; bear mirrors. A signal closes the other side and enters at the close; stop = close -/+ 1.2 ATR14, target = 1.5R, kept per direction. A position (as of a bar's close) issues the
same-direction exit, working from the next bar."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_vwap, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "qPXMv5X4"


def check():
    df = bars(14000, seed=210, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    lag = 16
    zl = np_ema(c + (c - np.r_[[np.nan] * lag, c[:-lag]]), 34)
    vw = np_vwap(df, (h + l + c) / 3)
    hl3 = (h + l + c) / 3
    dev = pd.Series(hl3).rolling(50).std(ddof=0).to_numpy()
    atr = np_atr(h, l, c, 14)
    body = np.abs(c - o)
    lw = np.minimum(o, c) - l
    uw = h - np.maximum(o, c)
    o1 = np.r_[np.nan, o[:-1]]
    with np.errstate(invalid="ignore"):
        br = (body > 0) & (lw > body) & (uw <= body * 1.2)
        sr = (body > 0) & (uw > body) & (lw <= body * 1.2)
        bull = (c > zl) & (c > vw) & ((l <= vw) | (l <= vw - dev) | (l <= zl)) & (br | (c > o)) & (c > o) & (c >= o1)
        bear = (c < zl) & (c < vw) & ((h >= vw) | (h >= vw + dev) | (h >= zl)) & (sr | (c < o)) & (c < o) & (c <= o1)
    s = dict(last=0)
    lvl = {}
    poscl = np.zeros(n)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if bull[i] and s["last"] != 1:
            r = atr[i] * 1.2
            lvl[1] = (c[i] - r, c[i] + r * 1.5)
            s["last"] = 1
            out += [("close", -1), ("entry", 1)]
        if bear[i] and s["last"] != -1:
            r = atr[i] * 1.2
            lvl[-1] = (c[i] + r, c[i] - r * 1.5)
            s["last"] = -1
            out += [("close", 1), ("entry", -1)]
        return out

    def stop(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0:
            return None
        return lvl[1 if pos > 0 else -1][0]

    def target(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0:
            return None
        return lvl[1 if pos > 0 else -1][1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
