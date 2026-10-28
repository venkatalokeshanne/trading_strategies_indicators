"""Independent check — Swing Breakout quant-core (SFnKkOyk): daily bars, long only. Close > SMA50 > SMA200, close above the highest close of the 50 bars before this one and volume >= 1.5 * SMA50(volume) enter when flat.
While a position is open at a close: peak = highest high since the first such close, trail = running max of peak - 4 ATR14 (both reset when flat), and a stop at the trail is issued, working from the next bar. Slippage
(2 ticks) and margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "SFnKkOyk"


def check():
    df = bars(8000, seed=258)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    f, s, va, atr = np_sma(c, 50), np_sma(c, 200), np_sma(v, 50), np_atr(h, l, c, 14)
    ph = pd.Series(c).shift(1).rolling(50).max().to_numpy()
    with np.errstate(invalid="ignore"):
        go = (c > f) & (c > s) & (f > s) & (c > ph) & (v >= 1.5 * va)
    peak = trail = np.nan
    lvl, poscl = np.full(n, np.nan), np.zeros(n)

    def orders(i, pos):
        nonlocal peak, trail
        poscl[i] = pos
        out = [("entry", 1)] if go[i] and pos == 0 else []
        if pos > 0:
            peak = h[i] if np.isnan(peak) else max(peak, h[i])
            cand = peak - 4.0 * atr[i]
            trail = cand if np.isnan(trail) else (np.nan if np.isnan(cand) else max(trail, cand))
            lvl[i] = trail
        else:
            peak = trail = np.nan
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: None if (i == 0 or poscl[i - 1] <= 0 or np.isnan(lvl[i - 1])) else lvl[i - 1])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
