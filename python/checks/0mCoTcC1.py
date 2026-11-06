"""Independent check — KDJ L2 (0mCoTcC1): hourly bars, process_orders_on_close (fills at the signal close), long only. RSV from an 18-bar range, K and D via the
author's "xsa" smoother (sumf := nz(sumf[1]) - nz(src[len]) + src; ma := na(src[len]) ? na : sumf/len; out := na(out[1]) ? ma : (src*wei + out[1]*(len-wei))/len),
J = 3K - 2D. Long when J crosses over 0; the long closes when J crosses under 100 or J crosses under K while J > 50 (close() acts only on an open trade).
Written as plain loops with Pine's nz() semantics. Slippage (1 tick) is 0 on both sides."""
import numpy as np

from indep import bars, compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "0mCoTcC1"


def nz(x):
    return 0.0 if np.isnan(x) else x


def xsa(src, length, wei):
    n = len(src)
    sumf, out = np.full(n, np.nan), np.full(n, np.nan)
    for i in range(n):
        prev_sum = sumf[i - 1] if i else np.nan
        lagged = src[i - length] if i - length >= 0 else np.nan
        sumf[i] = nz(prev_sum) - nz(lagged) + src[i]
        ma = np.nan if np.isnan(lagged) else sumf[i] / length
        prev_out = out[i - 1] if i else np.nan
        out[i] = ma if np.isnan(prev_out) else (src[i] * wei + prev_out * (length - wei)) / length
    return out


def cross(a, b, over):
    pa, pb = np.r_[np.nan, a[:-1]], np.r_[np.nan, b[:-1]] if np.ndim(b) else np.full(len(a), np.nan)
    b = np.broadcast_to(np.asarray(b, float), a.shape)
    pb = np.r_[np.nan, b[:-1]]
    with np.errstate(invalid="ignore"):
        return ((a > b) & (pa <= pb)) if over else ((a < b) & (pa >= pb))


def check():
    df = bars(12000, seed=153, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    lo, hi = np.full(n, np.nan), np.full(n, np.nan)
    for i in range(17, n):
        lo[i], hi[i] = l[i - 17:i + 1].min(), h[i - 17:i + 1].max()
    with np.errstate(invalid="ignore", divide="ignore"):
        rsv = (c - lo) / (hi - lo) * 100
    k = xsa(rsv, 4, 1)
    d = xsa(k, 4, 1)
    j = 3 * k - 2 * d
    lc = cross(j, np.zeros(n) + 0.0, True)
    ex = cross(j, np.zeros(n) + 100.0, False) | (cross(j, k, False) & (j > 50))
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if lc[i] else []) + ([("close", 1)] if ex[i] and pos > 0 else []),
                   on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
