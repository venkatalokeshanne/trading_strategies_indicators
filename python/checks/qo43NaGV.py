"""Independent check — Qing BB + MACD (qo43NaGV): daily bars, long only. BB(20, 2) population stdev; MACD(6, 12, 8) = EMA6 - EMA12, signal = EMA8 of it, hist = macd - signal. Entry: (close crossing over the basis while macd > signal, hist > 0 and rising, or MACD crossing over signal with close > basis
and hist > 0) and volume >= SMA20 and bullish candle. Exit (only if long): highest high of 3 bars >= previous upper band with two falling hist bars and a stalling bearish bar, or close < basis - 0.5 ATR14 on a bearish bar, or close > upper with macd > 0 and macd > 2.5 x signal."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_cross_over, np_ema, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "qo43NaGV"


def check():
    df = bars(9000, seed=58)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    basis = np_sma(c, 20)
    upper = basis + 2.0 * pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    macd = np_ema(c, 6) - np_ema(c, 12)
    sig = np_ema(macd, 8)
    hist = macd - sig
    atr = np_atr(h, l, c, 14)
    hist1, hist2 = np.r_[np.nan, hist[:-1]], np.r_[[np.nan] * 2, hist[:-2]]
    c1, up1 = np.r_[np.nan, c[:-1]], np.r_[np.nan, upper[:-1]]
    hh3 = pd.Series(h).rolling(3).max().to_numpy()
    with np.errstate(invalid="ignore"):
        solid = (macd > sig) & (hist > 0) & (hist > hist1)
        pb = np_cross_over(c, basis) & solid
        mb = np_cross_over(macd, sig) & (c > basis) & (hist > 0)
        entry = (pb | mb) & (v >= np_sma(v, 20)) & (c > o)
        dist = (hh3 >= up1) & (hist < hist1) & (hist1 < hist2) & (c < o) & (c <= c1)
        trend_end = (c < basis - atr * 0.5) & (c < o)
        exh = (c > upper) & (macd > 0) & (macd > sig * 2.5)
        ex = dist | trend_end | exh

    def orders(i, pos):
        out = []
        if entry[i]:
            out.append(("entry", 1))
        if ex[i] and pos > 0:
            out.append(("close", 1))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
