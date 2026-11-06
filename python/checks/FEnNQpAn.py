"""Independent check — RORO System Oscillator (FEnNQpAn): daily bars, long only, 1 unit. trend = norm(20 x (ALMA24(0.85, 6) - VWMA120) / VWMA120), momentum = norm(ROC14 / stdev50(ROC14)), norm(x) = x / (1 + |x|), score = 0.6 trend + 0.4
momentum, osc = clip(100 x score, -100, 100), smoothed by the same ALMA (unfloored offset x (n-1), weights exp(-(i - m)^2 / (2 (n / sigma)^2)), i = 0 at the oldest bar; na anywhere in the window = na). Buy at the next open when the smoothed oscillator
crosses up through +30 (previous <= 30 and now > 30); close when it is below -10. No trade statistics are checked. Margin and slippage off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "FEnNQpAn"


def alma(x, n=24, off=0.85, sg=6.0):
    out = np.full(len(x), np.nan)
    m, s = off * (n - 1), n / sg
    w = np.exp(-((np.arange(n) - m) ** 2) / (2 * s * s))
    for i in range(n - 1, len(x)):
        win = x[i - n + 1:i + 1]
        if not np.isnan(win).any():
            out[i] = np.sum(win * w) / np.sum(w)
    return out


def check():
    df = bars(5000, seed=738)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    a = alma(c)
    pv = pd.Series(c * v).rolling(120).sum().to_numpy()
    vv = pd.Series(v).rolling(120).sum().to_numpy()
    vw = pv / vv
    roc = 100.0 * (c - np.r_[np.full(14, np.nan), c[:-14]]) / np.r_[np.full(14, np.nan), c[:-14]]
    rv = pd.Series(roc).rolling(50).std(ddof=0).to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        tn = (a - vw) / vw * 20
        trend = tn / (1 + np.abs(tn))
        mm = roc / rv
        mom = mm / (1 + np.abs(mm))
        osc = np.clip((trend * 0.6 + mom * 0.4) * 100, -100, 100)
    sm = alma(osc)
    prev = np.r_[np.nan, sm[:-1]]
    with np.errstate(invalid="ignore"):
        lc = (sm > 30) & (prev <= 30)
        ex = sm < -10

    def orders(i, pos):
        out = []
        if lc[i]:
            out.append(("entry", 1))
        if ex[i] and pos > 0:
            out.append(("close", 1))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
