"""Independent check — Supertrend+atr (bK7ooPvS): daily bars, mintick 0.5 (so the trail amounts of 1.5 ATR read as ticks are ~0.75 ATR, passed to both sides). Hand-written Supertrend: up = hl2 - 3 ATR10 (kept at max(up, up1) while the
previous close is above up1), dn mirrored, trend flips on a close beyond the previous bar's dn / up; a flip not in "consolidation" (ATR10 < 0.5 * SMA20 of ATR14) reverses (close of the other id, then the entry). The exit
(trailing only: trail_points = trail_offset = 1.5 ATR in ticks, activation and offset both from the signal bar's ATR) is issued with the entry. Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_atr, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "bK7ooPvS"
TICK = 0.5


def nmax(a, b):
    return np.nan if (np.isnan(a) or np.isnan(b)) else max(a, b)


def nmin(a, b):
    return np.nan if (np.isnan(a) or np.isnan(b)) else min(a, b)


def check():
    df = bars(8000, seed=240)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr10, atr14 = np_atr(h, l, c, 10), np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        filt = atr10 < np_sma(atr14, 20) * 0.5
    hl2 = (h + l) / 2
    up_p = dn_p = np.nan
    tr_p = None
    buy, sell = np.zeros(n, bool), np.zeros(n, bool)
    for i in range(n):
        up = hl2[i] - 3.0 * atr10[i]
        up1 = up if np.isnan(up_p) else up_p
        c1 = c[i - 1] if i else np.nan
        if c1 > up1:
            up = nmax(up, up1)
        dn = hl2[i] + 3.0 * atr10[i]
        dn1 = dn if np.isnan(dn_p) else dn_p
        if c1 < dn1:
            dn = nmin(dn, dn1)
        trend = 1 if tr_p is None else tr_p
        if trend == -1 and c[i] > dn1:
            trend = 1
        elif trend == 1 and c[i] < up1:
            trend = -1
        buy[i] = trend == 1 and tr_p == -1
        sell[i] = trend == -1 and tr_p == 1
        up_p, dn_p, tr_p = up, dn, trend
    lvl = {1: np.nan, -1: np.nan}

    def orders(i, pos):
        out = []
        can = not filt[i]
        if buy[i] and can:
            out += [("close", -1), ("entry", 1)]; lvl[1] = atr10[i] * 1.5
        if sell[i] and can:
            out += [("close", 1), ("entry", -1)]; lvl[-1] = atr10[i] * 1.5
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, trail=lambda i, pos, ep, eb: (lvl[pos], lvl[pos]), tick=TICK)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9, mintick=TICK)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
