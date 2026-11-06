"""Independent check — Sweep + SD + MA20/50 + ATR (3uS01cPF): hourly bars. A pivot high / low (5 bars each side, strict on continuous prices) confirmed 5 bars later sets supplyTop = that bar's high / demandBottom = its low.
Long when flat: low below demandBottom, close back above it, the sweep deeper than 0.5 ATR, SMA20 > SMA50 with both rising and spread > 0.2 ATR (short mirrored with supplyTop). Signal bar issues entry + exit (stop = bar
low / high, limit = 3 R), so the bracket works from the fill bar. Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_atr, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "3uS01cPF"
K = 5


def check():
    df = bars(30000, seed=245, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    m20, m50, atr = np_sma(c, 20), np_sma(c, 50), np_atr(h, l, c, 14)
    m20p, m50p = np.r_[np.nan, m20[:-1]], np.r_[np.nan, m50[:-1]]
    with np.errstate(invalid="ignore"):
        bull = (m20 > m50) & (m20 > m20p) & (m50 > m50p)
        bear = (m20 < m50) & (m20 < m20p) & (m50 < m50p)
        valid = np.abs(m20 - m50) > atr * 0.2
    sup = dem = np.nan
    lvl = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}

    def orders(i, pos):
        nonlocal sup, dem
        if i >= 2 * K:
            j = i - K
            if h[j] > h[j - K:j].max() and h[j] > h[j + 1:i + 1].max():
                sup = h[j]
            if l[j] < l[j - K:j].min() and l[j] < l[j + 1:i + 1].min():
                dem = l[j]
        out = []
        with np.errstate(invalid="ignore"):
            ls = (not np.isnan(dem)) and l[i] < dem and c[i] > dem and (dem - l[i]) > atr[i] * 0.5
            ss = (not np.isnan(sup)) and h[i] > sup and c[i] < sup and (h[i] - sup) > atr[i] * 0.5
            if ls and bull[i] and valid[i] and pos == 0:
                out.append(("entry", 1)); lvl[1] = (l[i], c[i] + (c[i] - l[i]) * 3.0)
            if ss and bear[i] and valid[i] and pos == 0:
                out.append(("entry", -1)); lvl[-1] = (h[i], c[i] - (h[i] - c[i]) * 3.0)
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: lvl[pos][0], target=lambda i, pos, ep, eb: lvl[pos][1])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
