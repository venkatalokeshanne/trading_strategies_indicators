"""Independent check — Rudy Squeeze Detect v2 (XG0QegHh; k1yakMMf is the same script): daily bars, long only. Score = (volume ratio > 1.5: 2, > 1.2: 1) + (one-bar gap % > 3: 2, > 1: 1) + EMA21 > EMA50 + close > EMA21 + (BB width % < 5)
+ (5-bar momentum % > 2). Buys when flat if close > EMA21, RSI14 < 80 and score >= 3. While a position is open at a close a trailing exit (trail_points = 4 % and offset 0.5 % of that close in ticks of 0.01) works from the next
bar. Close < EMA21 and momentum < -3 % closes at the next open. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "XG0QegHh"
SEED = 295
TICK = 0.01


def build(tv_id, seed):
    df = bars(8000, seed=seed)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    sm, md, rsi = np_ema(c, 21), np_ema(c, 50), np_rsi(c, 14)
    vr = v / np_sma(v, 20)
    c1, c5 = np.r_[np.nan, c[:-1]], np.r_[np.full(5, np.nan), c[:-5]]
    gap = (c - c1) / c1 * 100
    mid = np_sma(c, 20)
    sd = pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    bbw = 4 * sd / mid * 100
    mom5 = (c - c5) / c5 * 100
    with np.errstate(invalid="ignore"):
        score = (np.where(vr > 1.5, 2, np.where(vr > 1.2, 1, 0)) + np.where(gap > 3.0, 2, np.where(gap > 1.0, 1, 0))
                 + (sm > md) + (c > sm) + (bbw < 5.0) + (mom5 > 2.0))
        buy = (c > sm) & (rsi < 80) & (score >= 3)
        fade = (c < sm) & (mom5 < -3.0)

    def orders(i, pos):
        out = []
        if buy[i] and pos == 0:
            out.append(("entry", 1))
        if fade[i] and pos > 0:
            out.append(("close", 1))
        return out

    ref = simulate(o, h, l, c, orders, trail=lambda i, pos, ep, eb: None if eb >= i else (c[i - 1] * 0.04 / TICK, c[i - 1] * 0.005 / TICK), tick=TICK)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(tv_id, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"


def check():
    return build(TV_ID, SEED)
