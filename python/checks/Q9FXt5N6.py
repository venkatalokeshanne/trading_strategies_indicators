"""Independent check — EMA Pullback + ADX + CVD Divergence (Q9FXt5N6): hourly bars. EMA9/20 cross arms a wait flag (a bull cross also disarms sell and vice versa); pullback to either EMA + ADX(14) > 25 + price breaking the previous
10 bars' low / high while CVD (cumulative signed volume) does not + candle colour fires the signal and disarms the flag. Signal bar issues entry + exit (stop = 5-bar lowest low / highest high, limit = 3 R); a repeat signal on the
open side replaces the levels. Windows exclude the current bar (rolling over i-10..i-1). Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_adx, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "Q9FXt5N6"
LB = 10


def check():
    df = bars(30000, seed=222, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    cvd = np.cumsum(np.where(c > o, v, np.where(c < o, -v, 0.0)))
    prev = lambda s, f: getattr(pd.Series(s).shift(1).rolling(LB), f)().to_numpy()   # window of the LB bars BEFORE this one
    with np.errstate(invalid="ignore"):
        bull = (l < prev(l, "min")) & (cvd > prev(cvd, "min"))
        bear = (h > prev(h, "max")) & (cvd < prev(cvd, "max"))
    e9, e20 = np_ema(c, 9), np_ema(c, 20)
    bc, sc = np_cross_over(e9, e20), np_cross_under(e9, e20)
    adx = np_adx(h, l, c, 14)
    sl5 = pd.Series(l).rolling(5).min().to_numpy()
    sh5 = pd.Series(h).rolling(5).max().to_numpy()
    wb = ws = False
    lvl = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}

    def orders(i, pos):
        nonlocal wb, ws
        if bc[i]:
            wb, ws = True, False
        if sc[i]:
            ws, wb = True, False
        with np.errstate(invalid="ignore"):
            pb = wb and (l[i] <= e9[i] or l[i] <= e20[i])
            ps = ws and (h[i] >= e9[i] or h[i] >= e20[i])
            buy = pb and adx[i] > 25 and bull[i] and c[i] > o[i]
            sell = ps and adx[i] > 25 and bear[i] and c[i] < o[i]
        out = []
        if buy:
            wb = False
        if sell:
            ws = False
        if buy:
            out.append(("entry", 1)); lvl[1] = (sl5[i], c[i] + (c[i] - sl5[i]) * 3.0)
        if sell:
            out.append(("entry", -1)); lvl[-1] = (sh5[i], c[i] - (sh5[i] - c[i]) * 3.0)
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: lvl[pos][0], target=lambda i, pos, ep, eb: lvl[pos][1])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
