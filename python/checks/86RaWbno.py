"""Independent check — SMA Strategy (86RaWbno): 5-min bars. SMA5 crossing SMA9 enters long with stop = 5-bar low and a 2R target (shorts mirrored with the
5-bar high), only if the risk exceeds one tick (0.01); the bracket is placed with the entry so it works from the fill bar; opposite signals reverse."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "86RaWbno"


def roll(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


def check():
    df = bars(20000, seed=141, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    s5, s9 = np_sma(c, 5), np_sma(c, 9)
    up, dn = np_cross_over(s5, s9), np_cross_under(s5, s9)
    # ta.lowest/highest sit inside the signal blocks, so (LESSONS P5) each call site only ever sees the values of the bars it ran on:
    # the 5-value window is the last 5 SIGNAL bars' lows (long block) / highs (short block), not the last 5 chart bars.
    lows, highs = [], []
    cur = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}
    hist = []

    def orders(i, pos):
        out = []
        if up[i]:
            lows.append(l[i])
            ll = min(lows[-5:]) if len(lows) >= 5 else np.nan
            if (c[i] - ll) > 0.01:
                out.append(("entry", 1)); cur[1] = (ll, c[i] + (c[i] - ll) * 2)
        if dn[i]:
            highs.append(h[i])
            hh = max(highs[-5:]) if len(highs) >= 5 else np.nan
            if (hh - c[i]) > 0.01:
                out.append(("entry", -1)); cur[-1] = (hh, c[i] - (hh - c[i]) * 2)
        hist.append(dict(cur))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: hist[i - 1][pos][0] if i > 0 else None,
                       target=lambda i, pos, ep, eb: hist[i - 1][pos][1] if i > 0 else None)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
