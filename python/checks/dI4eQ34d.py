"""Independent check — RSI-Gauss-WiP (dI4eQ34d; nnsWae8h is the same script): daily bars, 6 poles here (passed to both sides), slippage 0. N-pole Gaussian filter y[i] = a^N s[i] + sum_{k=1..N} (-1)^(k+1) C(N,k) (1-a)^k y[i-k] (missing history 0, na source 0), alpha from beta = (1 - cos(2 pi/144)) / (1.414^(2/N) - 1) and alpha = -beta + sqrt(beta^2 + 2 beta);
applied to hlc3 and to the true range (first bar high-low), band = filter + 1.414 * filtered TR. Long when flat-or-not (entry ignored while long), filter rising, close > band, K > D of SMA3 of the 14-bar stoch of RSI14 and the 2018-01-01 UTC start has passed; the close crossing under the band closes it (next open)."""
import math

import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_under, np_rsi, np_sma, np_tr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "dI4eQ34d"
N = 6


def gauss(s, a, poles):
    n = len(s)
    y = np.zeros(n)
    x = 1 - a
    s = np.nan_to_num(s)
    for i in range(n):
        v = a ** poles * s[i]
        for k in range(1, poles + 1):
            t = math.comb(poles, k) * x ** k * (y[i - k] if i - k >= 0 else 0.0)
            v = v + t if k % 2 else v - t
        y[i] = v
    return y


def psma(x, n):
    x = np.asarray(x, float)
    nanc = np.r_[0, np.cumsum(np.isnan(x))]
    P = np.r_[0.0, np.cumsum(np.where(np.isnan(x), 0.0, x))]
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        if nanc[i + 1] - nanc[i - n + 1] == 0:
            out[i] = (P[i] - P[i - (n - 1)] + x[i]) / n
    return out


def check():
    df = bars(5000, seed=286)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    rsi = np_rsi(c, 14)
    hh = pd.Series(rsi).rolling(14, min_periods=1).max().to_numpy().copy()
    ll = pd.Series(rsi).rolling(14, min_periods=1).min().to_numpy().copy()
    hh[:13] = ll[:13] = np.nan
    with np.errstate(invalid="ignore", divide="ignore"):
        stoch = 100 * (rsi - ll) / (hh - ll)
    stoch[~np.isfinite(stoch)] = np.nan
    k = psma(stoch, 3)
    d = psma(k, 3)
    beta = (1 - math.cos(4 * math.asin(1) / 144)) / (1.414 ** (2.0 / N) - 1)
    alpha = -beta + math.sqrt(beta ** 2 + 2 * beta)
    filtn = gauss((h + l + c) / 3, alpha, N)
    filttr = gauss(np_tr(h, l, c, True), alpha, N)
    band = filtn + filttr * 1.414
    t0 = int(pd.Timestamp("2018-01-01", tz="UTC").value // 1_000_000)
    tf = df["time"].to_numpy() >= t0
    with np.errstate(invalid="ignore"):
        green = np.r_[False, filtn[1:] > filtn[:-1]]
        lc = green & (c > band) & (k > d) & tf
        cu = np_cross_under(c, band) & tf

    def orders(i, pos):
        out = []
        if lc[i]:
            out.append(("entry", 1))
        if cu[i] and pos > 0:
            out.append(("close", 1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Poles": N}, strategy_overrides={"slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
