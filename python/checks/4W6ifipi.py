"""Independent check — EMA + Ichimoku Base (4W6ifipi): daily bars, Take Profit % = 2 here (passed to both sides), pyramiding 10, 1 unit per trade (indep.simulate_pyr). A close crossing over EMA4 enters long, under enters short (stacking up to 10, opposite side reverses). Both exit orders are re-issued
every bar (the stop even while flat, so it protects an entry from its fill bar; the limit needs a position average): stop = Ichimoku base line (midpoint of the 10-bar high / low, current bar included), target = position average price (as of the previous script run, whichever direction was open) * (1 +/- 2%); they apply to all open trades of
their own direction from the next bar. A cross back through the EMA closes the open side (only if one exists)."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate_pyr
from pinelib import SymbolInfo

TV_ID = "4W6ifipi"
TP = 2.0


def check():
    df = bars(9000, seed=61)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ema = np_ema(c, 4)
    kij = (pd.Series(h).rolling(10).max().to_numpy() + pd.Series(l).rolling(10).min().to_numpy()) / 2
    up, dn = np_cross_over(c, ema), np_cross_under(c, ema)
    avg_at, lv = {}, {}

    def orders(i, pos):
        out = []
        if up[i]:
            out.append(("entry", 1))
        if dn[i]:
            out.append(("entry", -1))
        lv[i] = (kij[i], avg_at.get(i) if pos != 0 else None)      # the stop is issued even while flat (limit = na then)
        if pos > 0 and dn[i]:
            out.append(("close", 1))
        if pos < 0 and up[i]:
            out.append(("close", -1))
        return out

    def stop(i, d, trades):
        avg_at[i] = float(np.mean([t[2] for t in trades]))
        p = lv.get(i - 1) if i > 0 else None
        return None if p is None or np.isnan(p[0]) else p[0]

    def target(i, d, trades):
        p = lv.get(i - 1) if i > 0 else None
        if p is None or p[1] is None:
            return None
        return p[1] * (1 + TP / 100) if d > 0 else p[1] * (1 - TP / 100)

    with np.errstate(invalid="ignore"):
        ref = simulate_pyr(o, h, l, c, orders, pyramiding=10, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Take Profit %": TP},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
