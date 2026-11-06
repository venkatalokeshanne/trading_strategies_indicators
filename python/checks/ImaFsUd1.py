"""Independent check — Centered RSI +/-50 cross (ImaFsUd1): daily bars, mintick scaled to the price level (passed to both sides). RSI14 crossing over 25 (crsi -50) goes long, under 75 (crsi +50) short (reversing, 5 contracts).
Exits unconditional: profit = 31 ticks, loss = ATR14 * 1.5 read as TICKS, re-issued every bar, so bar i uses bar i-1's ATR (also on a fill bar). Run twice: trailing off, and on (trail_points 8 / trail_offset 10 ticks, which
pinelib reads as activation 8 and offset 10)."""
import numpy as np

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "ImaFsUd1"


def check():
    df = bars(6000, seed=209)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    tick = round(float(c.mean()) * 0.003, 6)
    rsi, atr = np_rsi(c, 14), np_atr(h, l, c, 14)
    crsi = (rsi - 50) * 2
    lg, sh = np_cross_over(crsi, -50), np_cross_under(crsi, 50)

    def orders(i, pos):
        return ([("entry", 1)] if lg[i] else []) + ([("entry", -1)] if sh[i] else [])

    def stop(i, pos, ep, eb):
        return None if i == 0 or np.isnan(atr[i - 1]) else ep - pos * atr[i - 1] * 1.5 * tick

    def target(i, pos, ep, eb):
        return ep + pos * 31 * tick

    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9, mintick=tick)
    msgs, ok_all = [], True
    for trail_on in (False, True):
        with np.errstate(invalid="ignore"):
            ref = simulate(o, h, l, c, orders, stop=stop, target=target, tick=tick,
                           trail=(lambda i, pos, ep, eb: (8, 10)) if trail_on else None)
        params = {"Use Trailing Stop?": True} if trail_on else None
        ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params,
                                            strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
        ok_all = ok_all and ok and len(ref) > 10
        msgs.append(f"trail={'on' if trail_on else 'off'}: {detail} ({len(ref)})")
    return ok_all, "; ".join(msgs)
