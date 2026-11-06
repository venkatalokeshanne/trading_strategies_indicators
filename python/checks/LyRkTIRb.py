"""Independent check — Rudy Energy GC v2 (LyRkTIRb): daily bars, long only. EMA50 > SMA200, RSI14 < 75, close > EMA21 and strength (2 regime, +1 RSI<65, +1 close over SMA200 by >5 %, +1 close > EMA21) >= 3 enter when flat.
While a position is open at a close, a trailing exit is re-issued with trail_points = 8 % of that close and trail_offset = 1 % of it, in ticks (mintick 0.01); it works from the next bar. EMA50 < SMA200 closes the long at
the next open. Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "LyRkTIRb"
TICK = 0.01


def check():
    df = bars(6000, seed=218)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    f, s, t, rsi = np_ema(c, 50), np_sma(c, 200), np_ema(c, 21), np_rsi(c, 14)
    with np.errstate(invalid="ignore", divide="ignore"):
        mom = (c - s) / s * 100
        strength = 2 * (f > s) + (rsi < 65) + (mom > 5) + (c > t)
        go = (f > s) & (rsi < 75) & (c > t) & (strength >= 3)
        bear = f < s

    def orders(i, pos):
        out = []
        if go[i] and pos == 0:
            out.append(("entry", 1))
        if bear[i] and pos > 0:
            out.append(("close", 1))
        return out

    def trail(i, pos, ep, eb):
        if eb >= i:
            return None
        return (c[i - 1] * 0.08 / TICK, c[i - 1] * 0.01 / TICK)

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, trail=trail, tick=TICK)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
