"""Independent check — AXIS REVERSAL (ZyJPE4QX): daily bars. Hand-written Supertrend (ATR10 x 2 around hl2: up/dn stick to the previous value while the previous close stays on the right side, trend flips on a close beyond
the previous bar's dn / up); a close above the 50-bar highest high compared 5 bars back (a new high level) while trend is up arms the top switch (cleared when trend turns down), lows likewise for the bottom switch. When a
switch clears and RSI beyond 70 / 30 was seen within 10 bars the reversal enters short / long. Exits unconditional at the position's average price as of the previous close (1 % stop, 1.5 % target; OLD average on a
reversal's first bar; none on a fill bar). Margin off on the pinelib side (the original runs 10 % margin)."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "ZyJPE4QX"


def check():
    df = bars(8000, seed=254)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    rsi, atr = np_rsi(c, 14), np_atr(h, l, c, 10)
    hl2 = (h + l) / 2
    hi50 = pd.Series(h).rolling(50).max().to_numpy()
    lo50 = pd.Series(l).rolling(50).min().to_numpy()
    step = 5
    up_p = dn_p = np.nan
    trend = 1
    ha = la = ts = bs = 0
    since_lo = since_hi = np.nan
    rev_b, rev_s = np.zeros(n, bool), np.zeros(n, bool)
    for i in range(n):
        c1 = c[i - 1] if i else np.nan
        up = max(hl2[i] - 2 * atr[i], up_p) if c1 > up_p else hl2[i] - 2 * atr[i]       # NaN comparisons are false; max only runs when up_p is a number
        if c1 > up_p and (np.isnan(hl2[i] - 2 * atr[i])):
            up = np.nan
        dn = min(hl2[i] + 2 * atr[i], dn_p) if c1 < dn_p else hl2[i] + 2 * atr[i]
        if c1 < dn_p and (np.isnan(hl2[i] + 2 * atr[i])):
            dn = np.nan
        tprev = trend
        if trend == -1 and c[i] > dn_p:
            trend = 1
        elif trend == 1 and c[i] < up_p:
            trend = -1
        since_lo = 0 if rsi[i] < 30 else (np.nan if np.isnan(since_lo) else since_lo + 1)
        since_hi = 0 if rsi[i] > 70 else (np.nan if np.isnan(since_hi) else since_hi + 1)
        dn_zone = since_lo < 10 if not np.isnan(since_lo) else False
        up_zone = since_hi < 10 if not np.isnan(since_hi) else False
        if i >= step and not np.isnan(hi50[i - step]) and hi50[i] != hi50[i - step] and c[i] > hi50[i - step]:
            ha = 1
        if trend == -1 and tprev == 1:
            ha = 0
        if i >= step and not np.isnan(lo50[i - step]) and lo50[i] != lo50[i - step] and c[i] < lo50[i - step]:
            la = 1
        if trend == 1 and tprev == -1:
            la = 0
        ts_prev, bs_prev = ts, bs
        ts = 0 if (trend == -1 and tprev == 1) else (1 if (ha != 0 and trend == 1) else ts_prev)
        rev_s[i] = ts_prev == 1 and ts == 0 and up_zone
        bs = 0 if (trend == 1 and tprev == -1) else (1 if (la != 0 and trend == -1) else bs_prev)
        rev_b[i] = bs_prev == 1 and bs == 0 and dn_zone
        up_p, dn_p = up, dn
    ep_now, avg_close = {}, np.full(n, np.nan)

    def orders(i, pos):
        avg_close[i] = ep_now.get(i, np.nan) if pos != 0 else np.nan
        return ([("entry", 1)] if rev_b[i] else []) + ([("entry", -1)] if rev_s[i] else [])

    def level(k):
        def fn(i, pos, ep, eb):
            ep_now[i] = ep
            if i == 0 or np.isnan(avg_close[i - 1]):
                return None
            a = avg_close[i - 1]
            if pos > 0:
                return a * 0.99 if k == 0 else a * 1.015
            return a * 1.01 if k == 0 else a * 0.985
        return fn

    ref = simulate(o, h, l, c, orders, stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
