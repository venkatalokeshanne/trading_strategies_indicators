"""Independent check — Yuri Garcia Narrow State (x39mKkAp): hourly bars, mintick 0.01. Narrow state = |EMA20 - SMA200| / SMA200 * 100 <= 1.5. Uptrend (close and EMA20 above SMA200): a big green bar (body > 1.5 ATR14) or a green bar
closing above the previous high after a red bar enters long when not already long (downtrend mirror), subject to Trade Direction (Both / Buy Only / Sell Only). The exits are unconditional (stop = close -/+ 2 ATR, limit = close +/-
4 ATR, rounded half-up to the tick): bar i works with bar i-1's levels for its direction, also on a fill bar. Run for the three settings. Margin off on the pinelib side."""
import math

import numpy as np

from indep import bars, compare, np_atr, np_ema, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "x39mKkAp"
TICK = 0.01


def rnd(x):
    return np.floor(x / TICK + 0.5) * TICK


def check():
    df = bars(40000, seed=307, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr, e20, s200 = np_atr(h, l, c, 14), np_ema(c, 20), np_sma(c, 200)
    c1, o1, h1, l1 = (np.r_[np.nan, x[:-1]] for x in (c, o, h, l))
    with np.errstate(invalid="ignore", divide="ignore"):
        narrow = np.abs(e20 - s200) / s200 * 100 <= 1.5
        bt, bear = (c > s200) & (e20 > s200), (c < s200) & (e20 < s200)
        ele = np.abs(c - o) > atr * 1.5
        cl = ((ele & (c > o) & bt) | (bt & (c1 < o1) & (c > o) & (c > h1))) & narrow
        cs = ((ele & (c < o) & bear) | (bear & (c1 > o1) & (c < o) & (c < l1))) & narrow
        lsl, ltp = rnd(c - atr * 2.0), rnd(c + atr * 4.0)
        ssl, stp = rnd(c + atr * 2.0), rnd(c - atr * 4.0)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    msgs, ok_all = [], True
    for mode in ("Both", "Buy Only", "Sell Only"):
        buy, sell = mode in ("Both", "Buy Only"), mode in ("Both", "Sell Only")

        def orders(i, pos, buy=buy, sell=sell):
            out = []
            if cl[i] and buy and pos <= 0:
                out.append(("entry", 1))
            if cs[i] and sell and pos >= 0:
                out.append(("entry", -1))
            return out

        def stop(i, pos, ep, eb):
            if i == 0:
                return None
            v = lsl[i - 1] if pos > 0 else ssl[i - 1]
            return None if np.isnan(v) else v

        def target(i, pos, ep, eb):
            if i == 0:
                return None
            v = ltp[i - 1] if pos > 0 else stp[i - 1]
            return None if np.isnan(v) else v

        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
        ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", params={"Trade Direction": mode},
                                            strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
        ok_all = ok_all and ok and len(ref) > 5
        msgs.append(f"{mode}: {detail} ({len(ref)})")
    return ok_all, "; ".join(msgs)
