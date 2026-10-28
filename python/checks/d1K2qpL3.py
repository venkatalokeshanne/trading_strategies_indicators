"""Independent check — BTC 4H Momentum Long Only (d1K2qpL3): 5-min bars, long only. Close above a rising EMA200 (vs 10 bars ago), 20-bar ROC > 1 % and ADX(14) > 20,
only when flat; stop = the signal bar's 7-bar low, target = close + 3R, placed with the entry (works from the fill bar). Slippage (2 ticks) is 0 on both
sides: indep.simulate models slippage on market fills only."""
import numpy as np

from indep import bars, compare, np_adx, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "d1K2qpL3"


def roll(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


def check():
    df = bars(30000, seed=150, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    e = np_ema(c, 200)
    e10 = np.r_[[np.nan] * 10, e[:-10]]
    c20 = np.r_[[np.nan] * 20, c[:-20]]
    roc = (c - c20) / c20 * 100
    sw = roll(l, 7, np.min)
    adx = np_adx(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        go = (c > e) & (e > e10) & (roc > 1.0) & (adx > 20)
    cur = [(np.nan, np.nan)]
    hist = []

    def orders(i, pos):
        out = []
        if go[i] and pos == 0:
            out.append(("entry", 1)); cur[0] = (sw[i], c[i] + (c[i] - sw[i]) * 3.0)
        hist.append(cur[0])
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: hist[i - 1][0] if i > 0 else None,
                       target=lambda i, pos, ep, eb: hist[i - 1][1] if i > 0 else None)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
