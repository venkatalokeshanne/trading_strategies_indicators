"""Independent check — Ichimoku ATR Chikou (nOFDY1CW): daily bars. Entry as in the Chikou-touch script (Tenkan vs Kijun, close - close[25], close beyond the cloud top / bottom 25 bars back; every signal bar enters, reversing).
entry_price = the close of the first bar on which the position is open at the close; profit = close - entry_price (short mirrored); the Chikou touch (cross of the close with close[25]) exits only when profit > 1.5 ATR14; an
opposite Ichimoku signal always exits. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "nOFDY1CW"


def mid(h, l, n):
    return (pd.Series(l).rolling(n).min().to_numpy() + pd.Series(h).rolling(n).max().to_numpy()) / 2


def shift(x, k):
    return np.r_[np.full(k, np.nan), x[:-k]]


def check():
    df = bars(6000, seed=288)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    tk, kj, sb = mid(h, l, 9), mid(h, l, 26), mid(h, l, 52)
    sa = (tk + kj) / 2
    a25, b25 = shift(sa, 25), shift(sb, 25)
    top = np.where(np.isnan(a25) | np.isnan(b25), np.nan, np.maximum(a25, b25))
    bot = np.where(np.isnan(a25) | np.isnan(b25), np.nan, np.minimum(a25, b25))
    pl, pl1, c1 = shift(c, 25), shift(c, 26), shift(c, 1)
    atr = np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        bull = (tk > kj) & (c - pl > 0) & (c > top)
        bear = (tk < kj) & (c - pl < 0) & (c < bot)
        cr = ((c > pl) & (c1 <= pl1)) | ((c < pl) & (c1 >= pl1))
    st = dict(prev=0, ep=0.0)

    def orders(i, pos):
        if pos != 0 and st["prev"] == 0:
            st["ep"] = c[i]
        st["prev"] = pos
        profit = (c[i] - st["ep"]) if pos > 0 else ((st["ep"] - c[i]) if pos < 0 else 0.0)
        with np.errstate(invalid="ignore"):
            active = bool(profit > atr[i] * 1.5)
        out = []
        if bull[i]:
            out.append(("entry", 1))
        if bear[i]:
            out.append(("entry", -1))
        if pos > 0 and active and cr[i]:
            out.append(("close", 1))
        if pos < 0 and active and cr[i]:
            out.append(("close", -1))
        if pos > 0 and bear[i]:
            out.append(("close", 1))
        if pos < 0 and bull[i]:
            out.append(("close", -1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
