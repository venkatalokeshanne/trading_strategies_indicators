"""Independent check — SMC Trap → FVG (qX06Avws): hourly bars. Trap: high above the previous 10-bar highest high (the 10 bars BEFORE this one), close back below it and upper wick >= 10 % of the range (bear trap mirrored with the
lows), 3-bar cooldown per side. Every bullish (high[2] < low) / bearish (low[2] > high) 3-bar gap is appended to plain Python lists; a bear trap looks back for the newest bearish gap whose bottom is above the close (target), a bull
trap for the newest bullish gap whose top is below the close. Signal bar issues entry + exit (stop = bar low -/+ 0.3 ATR, limit = target), so the bracket works from the fill bar; both traps on one bar queue long then short.
Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "qX06Avws"


def check():
    df = bars(30000, seed=238, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr = np_atr(h, l, c, 14)
    sh = pd.Series(h).shift(1).rolling(10).max().to_numpy()
    sl_ = pd.Series(l).shift(1).rolling(10).min().to_numpy()
    rng = h - l
    with np.errstate(invalid="ignore", divide="ignore"):
        up = np.where(rng > 0, (h - np.maximum(o, c)) / rng, 0.0)
        lo = np.where(rng > 0, (np.minimum(o, c) - l) / rng, 0.0)
        rb = (h > sh) & (c < sh) & (up >= 0.1)
        rr = (l < sl_) & (c > sl_) & (lo >= 0.1)
    lbt = lrt = None
    tops, bots, bulls = [], [], []
    lvl = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}

    def orders(i, pos):
        nonlocal lbt, lrt
        bull_trap = rb[i] and (lbt is None or i - lbt > 3)
        bear_trap = rr[i] and (lrt is None or i - lrt > 3)
        if bull_trap:
            lbt = i
        if bear_trap:
            lrt = i
        if i >= 2:
            if h[i - 2] < l[i]:
                tops.append(l[i]); bots.append(h[i - 2]); bulls.append(True)
            if l[i - 2] > h[i]:
                tops.append(l[i - 2]); bots.append(h[i]); bulls.append(False)
        out = []
        if bear_trap:
            tp = np.nan
            for k in range(len(tops) - 1, -1, -1):
                if not bulls[k] and bots[k] > c[i]:
                    tp = bots[k]; break
            if not np.isnan(tp):
                out.append(("entry", 1)); lvl[1] = (l[i] - atr[i] * 0.3, tp)
        if bull_trap:
            tp = np.nan
            for k in range(len(tops) - 1, -1, -1):
                if bulls[k] and tops[k] < c[i]:
                    tp = tops[k]; break
            if not np.isnan(tp):
                out.append(("entry", -1)); lvl[-1] = (h[i] + atr[i] * 0.3, tp)
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: lvl[pos][0], target=lambda i, pos, ep, eb: lvl[pos][1])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
