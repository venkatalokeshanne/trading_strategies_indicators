"""Independent check — ATR Exhaustion & Volume Spike (8ltrS3Yg): hourly bars. Pivots (5 each side, strict) keep lastPH / lastPL (updated on the confirmation bar). Long: low within +/-0.5 % of lastPL, lastPH - low > 2 ATR14, volume > 1.5
SMA20, close > open or close > high[1], flat; stop = lastPL if lastPL < low else low, limit = close + 2 * (close - stop); short mirrored. Entry + exit on the signal bar (bracket works from the fill bar); quantity
(0.5 % of equity risk) never moves prices; no order when the risk distance is <= 0. Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_atr, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "8ltrS3Yg"
K = 5


def conf(x, high):
    n = len(x)
    out = np.full(n, np.nan)
    for i in range(2 * K, n):
        j = i - K
        if high and x[j] > x[j - K:j].max() and x[j] > x[j + 1:i + 1].max():
            out[i] = x[j]
        if (not high) and x[j] < x[j - K:j].min() and x[j] < x[j + 1:i + 1].min():
            out[i] = x[j]
    return out


def check():
    df = bars(30000, seed=305, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    cph, cpl = conf(h, True), conf(l, False)
    atr, vm = np_atr(h, l, c, 14), np_sma(v, 20)
    h1 = np.r_[np.nan, h[:-1]]
    l1 = np.r_[np.nan, l[:-1]]
    lph = lpl = np.nan
    lvl = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}

    def orders(i, pos):
        nonlocal lph, lpl
        if not np.isnan(cph[i]):
            lph = cph[i]
        if not np.isnan(cpl[i]):
            lpl = cpl[i]
        out = []
        with np.errstate(invalid="ignore"):
            spike = v[i] > vm[i] * 1.5
            nl = l[i] <= lpl * 1.005 and l[i] >= lpl * 0.995
            nh = h[i] >= lph * 0.995 and h[i] <= lph * 1.005
            lg = nl and (lph - l[i]) > atr[i] * 2.0 and spike and (c[i] > o[i] or c[i] > h1[i])
            sg = nh and (c[i] - lpl) > atr[i] * 2.0 and spike and (c[i] < o[i] or c[i] < l1[i])
            if lg and pos == 0:
                sl = lpl if lpl < l[i] else l[i]
                if c[i] - sl > 0:
                    out.append(("entry", 1)); lvl[1] = (sl, c[i] + (c[i] - sl) * 2.0)
            if sg and pos == 0:
                sl = lph if lph > h[i] else h[i]
                if sl - c[i] > 0:
                    out.append(("entry", -1)); lvl[-1] = (sl, c[i] - (sl - c[i]) * 2.0)
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: lvl[pos][0], target=lambda i, pos, ep, eb: lvl[pos][1])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
