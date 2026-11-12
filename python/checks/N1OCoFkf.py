"""Independent check — Bollinger Squeeze Breakout + Volume (N1OCoFkf): hourly bars. Band width = (upper - lower) / basis (20, 2 pop-stdev); squeeze when width < 0.8 * SMA50(width). On the bar AFTER a squeeze bar: close crossing over the
upper band (under the lower) with volume > SMA20 and flat enters long (short) with entry + exit on the signal bar (stop 1.5 ATR, limit 3 ATR around the close). v6 short-circuit: each cross runs only on bars after a squeeze bar,
against the last bar it ran on (LESSONS P4/P5). Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "N1OCoFkf"


def check():
    df = bars(40000, seed=249, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    basis = np_sma(c, 20)
    d = 2.0 * pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    up, lo = basis + d, basis - d
    with np.errstate(invalid="ignore", divide="ignore"):
        width = (up - lo) / basis
        sq = width < np_sma(width, 50) * 0.8
        vp = v > np_sma(v, 20)
    atr = np_atr(h, l, c, 14)
    pu, pl = [np.nan, np.nan], [np.nan, np.nan]
    lvl = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}

    def orders(i, pos):
        was = bool(sq[i - 1]) if i else False
        out = []
        xo = xu = False
        if was:
            xo = bool(c[i] > up[i] and pu[0] <= pu[1]); pu[0], pu[1] = c[i], up[i]
            xu = bool(c[i] < lo[i] and pl[0] >= pl[1]); pl[0], pl[1] = c[i], lo[i]
        if xo and vp[i] and pos == 0:
            out.append(("entry", 1)); lvl[1] = (c[i] - atr[i] * 1.5, c[i] + atr[i] * 3.0)
        if xu and vp[i] and pos == 0:
            out.append(("entry", -1)); lvl[-1] = (c[i] + atr[i] * 1.5, c[i] - atr[i] * 3.0)
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: lvl[pos][0], target=lambda i, pos, ep, eb: lvl[pos][1])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
