"""Independent check — Ichimoku Chikou Touch (ZtV3Wy3c): daily bars. Tenkan / Kijun / Senkou B = (lowest low + highest high) / 2 over 9 / 26 / 52 bars, Senkou A = (Tenkan + Kijun) / 2; the cloud is the value 25 bars back.
Long: Tenkan > Kijun, close - close[25] > 0, close above the cloud top (short mirrored), reversing. A position closes at the next open when the close touches or crosses close[25] (a cross: over or under, versus the previous
bar's close[25] i.e. close[26]). Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "ZtV3Wy3c"


def mid(h, l, n):
    return (pd.Series(l).rolling(n).min().to_numpy() + pd.Series(h).rolling(n).max().to_numpy()) / 2


def shift(x, k):
    return np.r_[np.full(k, np.nan), x[:-k]]


def check():
    df = bars(5000, seed=253)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    tk, kj, sb = mid(h, l, 9), mid(h, l, 26), mid(h, l, 52)
    sa = (tk + kj) / 2
    a25, b25 = shift(sa, 25), shift(sb, 25)
    top = np.where(np.isnan(a25) | np.isnan(b25), np.nan, np.maximum(a25, b25))
    bot = np.where(np.isnan(a25) | np.isnan(b25), np.nan, np.minimum(a25, b25))
    pl, pl1, c1 = shift(c, 25), shift(c, 26), shift(c, 1)
    with np.errstate(invalid="ignore"):
        bull = (tk > kj) & (c - pl > 0) & (c > top)
        bear = (tk < kj) & (c - pl < 0) & (c < bot)
        cr = ((c > pl) & (c1 <= pl1)) | ((c < pl) & (c1 >= pl1))

    def orders(i, pos):
        out = []
        if bull[i]:
            out.append(("entry", 1))
        if bear[i]:
            out.append(("entry", -1))
        if pos != 0 and cr[i]:
            out.append(("close", pos))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
