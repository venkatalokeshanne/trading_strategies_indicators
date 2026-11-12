"""Independent check — Hemant Gold Strategy (eyaf13E5): 5-min bars. Liquidity-sweep entries (low under the previous 10-bar low and a
close back above it, above EMA200; mirrored for shorts), reversing. Both exits are unconditional and use the position's average price
as of the previous bar's close (na while flat) and ATR 1.5 / 4.5, for BOTH directions, so a reversal's first bar uses the OLD average."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "eyaf13E5"


def roll(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


def check():
    df = bars(20000, seed=94, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    e200, atr = np_ema(c, 200), np_atr(h, l, c, 14)
    hh1 = np.r_[np.nan, roll(h, 10, np.max)[:-1]]
    ll1 = np.r_[np.nan, roll(l, 10, np.min)[:-1]]
    with np.errstate(invalid="ignore"):
        buy = (l < ll1) & (c > ll1) & (c > e200)
        sell = (h > hh1) & (c < hh1) & (c < e200)
    ep_now, avg_close = {}, np.full(n, np.nan)

    def orders(i, pos):
        avg_close[i] = ep_now.get(i, np.nan) if pos != 0 else np.nan
        out = []
        if buy[i] and pos <= 0:
            out.append(("entry", 1))
        if sell[i] and pos >= 0:
            out.append(("entry", -1))
        return out

    def level(k):
        def f(i, pos, ep, eb):
            ep_now[i] = ep
            if i == 0 or np.isnan(avg_close[i - 1]) or np.isnan(atr[i - 1]):
                return None
            a, r = avg_close[i - 1], atr[i - 1] * 1.5
            return (a - r if pos > 0 else a + r) if k == 0 else (a + 3 * r if pos > 0 else a - 3 * r)
        return f

    ref = simulate(o, h, l, c, orders, stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
