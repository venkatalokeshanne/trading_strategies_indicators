"""Independent check — Trend Pulse OBV (LBcj22se): daily bars, long only, 1 trade at a time, trade list only. hlc3 and the true range (first bar high - low) get the zero-lag transform x + (x - x[17]) (17 = int(143 / 8)); each is smoothed by four cascaded
EMAs of length max(1, int(2 / alpha)) with beta = (1 - cos(2 pi / 144)) / (1.414^(2/4) - 1), alpha = -beta + sqrt(beta^2 + 2 beta); upper band = filtered hlc3 + 1.414 x filtered TR. Buy at the next open when the close crosses over the upper band, close > EMA50(close) and
OBV > EMA60(OBV) (OBV = running sum of sign(change(close)) x volume, 0 on bar 0), from 2018-01-01 UTC. The ATR14 stop (signal close - 1.7 x ATR14 of the PREVIOUS bar) is cleared by the original's `if position_size == 0: stopPrice := na` on the very bar it is set (the position is still flat at script time), so no stop order ever exists. The trade closes at the next
open when the close is below the filter midline or below EMA50 (inside the date range). Margin, commission and slippage off on the pinelib side."""
import math

import numpy as np

from indep import bars, compare, np_atr, np_cross_over, np_ema, np_tr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "LBcj22se"


def cascade(x, ln):
    for _ in range(4):
        x = np_ema(x, ln)
    return x


def check():
    df = bars(6000, seed=494)
    t = df["time"].to_numpy()
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    hlc3 = (h + l + c) / 3
    tr = np_tr(h, l, c, True)
    lag = 17
    sin = hlc3 + (hlc3 - np.r_[np.full(lag, np.nan), hlc3[:-lag]])
    trin = tr + (tr - np.r_[np.full(lag, np.nan), tr[:-lag]])
    beta = (1 - math.cos(2 * math.pi / 144)) / (1.414 ** (2.0 / 4) - 1)
    alpha = -beta + math.sqrt(beta * beta + 2 * beta)
    ln = max(1, int(2.0 / alpha))
    filt, filt_tr = cascade(sin, ln), cascade(trin, ln)
    upper = filt + filt_tr * 1.414
    ch = np.r_[np.nan, np.diff(c)]
    obv = np.cumsum(np.where(np.isnan(ch), 0.0, np.sign(ch)) * v)        # bar 0: no change -> 0
    obv_ema = np_ema(obv, 60)
    reg = np_ema(c, 50)
    atr = np_atr(h, l, c, 14)
    atr1 = np.r_[np.nan, atr[:-1]]
    with np.errstate(invalid="ignore"):
        inr = (t >= 1514764800000) & (t <= 3155846340000)
        le = np_cross_over(c, upper) & (c > reg) & (obv > obv_ema) & inr
        lx = ((c < filt) | (c < reg)) & inr
    S = dict(stop=np.nan)
    poscl = np.zeros(n)
    stop_arr = np.full(n, np.nan)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if le[i] and pos == 0:
            out.append(("entry", 1))
            S["stop"] = c[i] - atr1[i] * 1.7
        if pos == 0:                       # the original clears the stop right after the entry (position still 0 at script time)
            S["stop"] = np.nan
        if pos > 0:
            stop_arr[i] = S["stop"]
        if lx[i] and pos > 0:
            out.append(("close", 1))
        return out

    def stop(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] <= 0 or np.isnan(stop_arr[i - 1]):
            return None
        return stop_arr[i - 1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "commission_value": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
