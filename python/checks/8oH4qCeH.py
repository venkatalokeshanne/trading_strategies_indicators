"""Independent check — RSI Divergence + EMA Trend Filter (8oH4qCeH): daily bars. Pivots (5 each side, strict) are confirmed 5 bars later; at the confirmation bars the bar's own `high` / `low` and RSI14 are recorded (valuewhen reads
the confirmation bar, not the pivot bar). Bear divergence = a confirmation of a pivot high now with high > the previous confirmation bar's high and RSI < its RSI (bull mirrored). Long needs bull divergence + close > EMA200 + flat; the
exit stop is low[5] - 1.5 ATR14 (the pivot bar's low), the limit close + 3 ATR14; both are issued on the signal bar, so the bracket works from the fill bar. Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "8oH4qCeH"
K = 5


def conf(x, high):
    n = len(x)
    out = np.zeros(n, bool)
    for i in range(2 * K, n):
        j = i - K
        if high and x[j] > x[j - K:j].max() and x[j] > x[j + 1:i + 1].max():
            out[i] = True
        if (not high) and x[j] < x[j - K:j].min() and x[j] < x[j + 1:i + 1].min():
            out[i] = True
    return out


def check():
    df = bars(12000, seed=284)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    rsi, e, atr = np_rsi(c, 14), np_ema(c, 200), np_atr(h, l, c, 14)
    cph, cpl = conf(h, True), conf(l, False)
    ph = dict(prev_h=np.nan, prev_r=np.nan)
    pl = dict(prev_l=np.nan, prev_r=np.nan)
    lvl = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}

    def orders(i, pos):
        out = []
        bear = bull = False
        with np.errstate(invalid="ignore"):
            if cph[i]:
                bear = bool(h[i] > ph["prev_h"] and rsi[i] < ph["prev_r"])
                ph.update(prev_h=h[i], prev_r=rsi[i])
            if cpl[i]:
                bull = bool(l[i] < pl["prev_l"] and rsi[i] > pl["prev_r"])
                pl.update(prev_l=l[i], prev_r=rsi[i])
            if bull and c[i] > e[i] and pos == 0:
                out.append(("entry", 1)); lvl[1] = (l[i - K] - atr[i] * 1.5, c[i] + atr[i] * 3.0)
            if bear and c[i] < e[i] and pos == 0:
                out.append(("entry", -1)); lvl[-1] = (h[i - K] + atr[i] * 1.5, c[i] - atr[i] * 3.0)
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: lvl[pos][0], target=lambda i, pos, ep, eb: lvl[pos][1])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
