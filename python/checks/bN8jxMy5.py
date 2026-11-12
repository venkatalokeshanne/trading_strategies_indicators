"""Independent check — Momentum Squeeze Breakout (bN8jxMy5): daily bars, long only, 100 % of equity. Squeeze = Bollinger(20, 2 pop-stdev) inside Keltner(SMA20 of true range x 1.5); barssince <= 3 (na never true).
Long on the close crossing over the upper band with SMA20 of the close-position bias > 0, close > EMA200, ROC(3) > 0; the close under the lower band with bias <= 0 closes the long. v6 short-circuit: both crosses run
only while a squeeze was recent, against the last bar they ran on (LESSONS P4/P5). Signals need bar_index > lastSignalBar + 15 (either side updates it). Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, np_sma, np_tr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "bN8jxMy5"


def check():
    df = bars(8000, seed=241)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    basis = np_sma(c, 20)
    dev = 2.0 * pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    ubb, lbb = basis + dev, basis - dev
    tr = np_sma(np_tr(h, l, c, False), 20)
    ukc, lkc = basis + tr * 1.5, basis - tr * 1.5
    with np.errstate(invalid="ignore"):
        sq = (lbb > lkc) & (ubb < ukc)
        rng = h - l
        cpos = np.where(rng == 0, 0.0, (c - l) / np.where(rng == 0, 1, rng) * 2.0 - 1.0)
    bias = np_sma(cpos, 20)
    e200 = np_ema(c, 200)
    c3 = np.r_[np.full(3, np.nan), c[:-3]]
    roc = 100 * (c - c3) / c3
    since = np.full(n, np.nan)
    cnt = np.nan
    for i in range(n):
        cnt = 0 if sq[i] else (np.nan if np.isnan(cnt) else cnt + 1)
        since[i] = cnt
    pu, pl = [np.nan, np.nan], [np.nan, np.nan]                      # (close, band) at the last bar each cross ran
    last = [0]

    def orders(i, pos):
        out = []
        recent = since[i] <= 3 if not np.isnan(since[i]) else False
        acc = dist = False
        if recent:
            xo = bool(c[i] > ubb[i] and pu[0] <= pu[1])
            pu[0], pu[1] = c[i], ubb[i]
            xu = bool(c[i] < lbb[i] and pl[0] >= pl[1])
            pl[0], pl[1] = c[i], lbb[i]
            acc = xo and bias[i] > 0 and c[i] > e200[i] and roc[i] > 0
            dist = xu and bias[i] <= 0
        if acc and i > last[0] + 15:
            out.append(("entry", 1)); last[0] = i
        if dist and i > last[0] + 15:
            out.append(("close", 1)); last[0] = i
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
