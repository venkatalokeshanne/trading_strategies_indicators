"""Independent check — FVG Continuation Framework (4uYwBCmZ): 5-min bars. A 3-bar gap (low above the high two bars ago) stores the bullish zone top
(this low); a later bar that dips to the zone and closes back above it with close > EMA50 buys (mirrored for bearish gaps), reversing. Both exits
are unconditional with ATR*1.5 stop / 3 ATR target around the position's average price as of the previous close (na while flat), for BOTH
directions (a reversal's first bar uses the OLD average). Margin is 100 % by default in v6 with 1 contract on a 100k account: off here."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "4uYwBCmZ"


def check():
    df = bars(20000, seed=124, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    e50, atr = np_ema(c, 50), np_atr(h, l, c, 14)
    h2, l2 = np.r_[[np.nan] * 2, h[:-2]], np.r_[[np.nan] * 2, l[:-2]]
    lg, sg = np.zeros(n, bool), np.zeros(n, bool)
    bt = bb = np.nan
    for i in range(n):
        if l[i] > h2[i]:
            bt = l[i]
        if h[i] < l2[i]:
            bb = h[i]
        lg[i] = not np.isnan(bt) and l[i] <= bt and c[i] > bt and c[i] > e50[i]
        sg[i] = not np.isnan(bb) and h[i] >= bb and c[i] < bb and c[i] < e50[i]
    ep_now, avg_close = {}, np.full(n, np.nan)

    def orders(i, pos):
        avg_close[i] = ep_now.get(i, np.nan) if pos != 0 else np.nan
        return ([("entry", 1)] if lg[i] and pos <= 0 else []) + ([("entry", -1)] if sg[i] and pos >= 0 else [])

    def level(k):
        def fn(i, pos, ep, eb):
            ep_now[i] = ep
            if i == 0 or np.isnan(avg_close[i - 1]) or np.isnan(atr[i - 1]):
                return None
            a, r = avg_close[i - 1], atr[i - 1] * 1.5
            return (a - r if pos > 0 else a + r) if k == 0 else (a + 2 * r if pos > 0 else a - 2 * r)
        return fn

    ref = simulate(o, h, l, c, orders, stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
