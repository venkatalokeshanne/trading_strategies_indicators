"""Independent check — RSI-Gauss-Velocity (oc2vZUcN; T5kd1bJ2 is the same script): daily bars, long only. 4-pole Gaussian filter y[i] = a^4 s[i] + 4(1-a) y[i-1] - 6(1-a)^2 y[i-2] + 4(1-a)^3 y[i-3] - (1-a)^4 y[i-4] (missing history = 0, na source = 0),
alpha from beta = (1 - cos(2 pi / 144)) / (1.414^(2/4) - 1); applied to hlc3 (filtn) and to the true range with na handling (filttr); band = filtn + 1.414 * filttr. Long when filtn rises, close > band, K > D of SMA3(stoch14(RSI14)) vs SMA3,
flat. Exit when the close crosses under the band, or slope < SMA20(slope) - stdev20(slope) while in profit and close < band (now or one bar ago). Slippage (3 ticks) and margin off on the pinelib side."""
import math

import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_under, np_rsi, np_sma, np_tr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "oc2vZUcN"
SEED = 287


def gauss(s, a, poles=4):
    n = len(s)
    y = np.zeros(n)
    x = 1 - a
    s = np.nan_to_num(s)
    for i in range(n):
        g = lambda k: y[i - k] if i - k >= 0 else 0.0
        y[i] = a ** 4 * s[i] + 4 * x * g(1) - 6 * x ** 2 * g(2) + 4 * x ** 3 * g(3) - x ** 4 * g(4)
    return y


def build(tv_id, seed):
    df = bars(5000, seed=seed)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    rsi = np_rsi(c, 14)
    hh = pd.Series(rsi).rolling(14, min_periods=1).max().to_numpy().copy()      # ta.highest / lowest skip na but need 14 bars
    ll = pd.Series(rsi).rolling(14, min_periods=1).min().to_numpy().copy()
    hh[:13] = np.nan
    ll[:13] = np.nan
    with np.errstate(invalid="ignore", divide="ignore"):
        stoch = 100 * (rsi - ll) / (hh - ll)
    stoch[~np.isfinite(stoch)] = np.nan
    k = np_sma(stoch, 3)
    d = np_sma(k, 3)
    beta = (1 - math.cos(4 * math.asin(1) / 144)) / (1.414 ** (2.0 / 4) - 1)
    alpha = -beta + math.sqrt(beta ** 2 + 2 * beta)
    filtn = gauss((h + l + c) / 3, alpha)
    filttr = gauss(np_tr(h, l, c, True), alpha)
    band = filtn + filttr * 1.414
    slope = np.r_[np.nan, np.diff(filtn)]
    smean = np_sma(slope, 20)
    sstd = pd.Series(slope).rolling(20).std(ddof=0).to_numpy()
    with np.errstate(invalid="ignore"):
        exh = slope < (smean - sstd)
        green = np.r_[False, filtn[1:] > filtn[:-1]]
        lc = green & (c > band) & (k > d)
        cu = np_cross_under(c, band)
    band1 = np.r_[np.nan, band[:-1]]
    ep = [np.nan]

    def orders(i, pos):
        out = []
        if lc[i]:
            out.append(("entry", 1))
            if pos == 0:
                ep[0] = o[i + 1] if i + 1 < n else np.nan
        inp = pos > 0 and c[i] > ep[0]
        with np.errstate(invalid="ignore"):
            ex = bool(cu[i] or (exh[i] and inp and (c[i] < band[i] or c[i] < band1[i])))
        if ex and pos > 0:
            out.append(("close", 1))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(tv_id, df, symbol=sym, tf="D", strategy_overrides={"slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"


def check():
    return build(TV_ID, SEED)
