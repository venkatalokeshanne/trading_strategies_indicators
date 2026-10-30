"""Independent check — Aroon Strategy Pro (vlBYB1vO): daily bars, one position, trade list only. Aroon-like lines upper = 100 x (offset of the highest high in the last 15 bars + 14) / 14 and lower likewise for the lowest low
(offsets <= 0; ties are not expected on continuous data). Long when lower crosses under upper (short: over) with close above (below) both SMA290 and EMA200, not in a trade, and more than one bar after the last exit. The signal bar
fixes entry = close, stop = entry -/+ 20 x 0.1, target = entry +/- 1.5 x that, break-even trigger = entry +/- 1 x. Each later bar (script level, state machine in the script) moves the stop to entry once the bar reaches the BE
trigger, then tests the bar's high / low against the target + 2 ticks and the stop; a hit issues a market close (next open) and starts the one-bar block. Margin and slippage off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "vlBYB1vO"


def check():
    df = bars(8000, seed=262)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    L = 14
    up = np.full(n, np.nan)
    lo = np.full(n, np.nan)
    for i in range(L, n):
        wh, wl = h[i - L:i + 1], l[i - L:i + 1]
        up[i] = 100 * ((np.argmax(wh) - L) + L) / L
        lo[i] = 100 * ((np.argmin(wl) - L) + L) / L
    sma, ema = np_sma(c, 290), np_ema(c, 200)
    with np.errstate(invalid="ignore"):
        tl = (c > sma) & (c > ema)
        ts = (c < sma) & (c < ema)
        ls = np_cross_under(lo, up) & tl
        ss = np_cross_over(lo, up) & ts
    S = dict(it=False, d=0, ep=0.0, sl=0.0, tp=0.0, be=0.0, last=0)

    def orders(i, pos):
        out = []
        if S["it"]:
            d = S["d"]
            if (d == 1 and h[i] >= S["be"]) or (d == -1 and l[i] <= S["be"]):
                S["sl"] = S["ep"]
            trig = S["tp"] + d * 2 * 0.01
            hit_tp = (d == 1 and h[i] >= trig) or (d == -1 and l[i] <= trig)
            hit_sl = (d == 1 and l[i] <= S["sl"]) or (d == -1 and h[i] >= S["sl"])
            if hit_tp or hit_sl:
                out.append(("close", d))
                S["it"] = False
                S["last"] = i
        can = i > S["last"] + 1
        for sig, d in ((ls[i], 1), (ss[i], -1)):
            if sig and not S["it"] and can:
                dist = 20.0 * 0.1
                S.update(it=True, d=d, ep=c[i], sl=c[i] - d * dist, tp=c[i] + d * dist * 1.5, be=c[i] + d * dist * 1.0)
                out.append(("entry", d))
                break
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
