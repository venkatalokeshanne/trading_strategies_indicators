"""Independent check — Pro Structure Momentum Bot A+ (x6xuv6rg): 5-min bars. A close above the previous bar's 10-bar high arms longLevel (below the
low: shortLevel); a later pullback to the level with a close back beyond it, the EMA9/21 trend and a confirming candle enters (and clears the
level). Exits unconditional: bar i works with bar i-1's 3-bar low/high stop and 2R target from that bar's close (also on the fill bar)."""
import numpy as np

from indep import bars, compare, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "x6xuv6rg"


def roll(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


def check():
    df = bars(20000, seed=121, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    e9, e21 = np_ema(c, 9), np_ema(c, 21)
    sh, sl = roll(h, 10, np.max), roll(l, 10, np.min)
    ll3, hh3 = roll(l, 3, np.min), roll(h, 3, np.max)
    buy, sell = np.zeros(n, bool), np.zeros(n, bool)
    lvl_l = lvl_s = np.nan
    for i in range(1, n):
        if c[i] > sh[i - 1]:
            lvl_l = sh[i - 1]
        if c[i] < sl[i - 1]:
            lvl_s = sl[i - 1]
        pl = not np.isnan(lvl_l) and l[i] <= lvl_l and c[i] > lvl_l
        ps = not np.isnan(lvl_s) and h[i] >= lvl_s and c[i] < lvl_s
        buy[i] = e9[i] > e21[i] and pl and c[i] > o[i] and c[i] > c[i - 1]
        sell[i] = e9[i] < e21[i] and ps and c[i] < o[i] and c[i] < c[i - 1]
        if buy[i]:
            lvl_l = np.nan
        if sell[i]:
            lvl_s = np.nan

    def stop(i, pos, ep, eb):
        if i == 0:
            return None
        return ll3[i - 1] if pos > 0 else hh3[i - 1]

    def target(i, pos, ep, eb):
        if i == 0:
            return None
        return c[i - 1] + (c[i - 1] - ll3[i - 1]) * 2 if pos > 0 else c[i - 1] - (hh3[i - 1] - c[i - 1]) * 2

    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if buy[i] else []) + ([("entry", -1)] if sell[i] else []),
                   stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
