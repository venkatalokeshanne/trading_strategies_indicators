"""Independent check — TZ Gold Round Levels (5zL50iGH): 15-minute bars, prices x5 (~500) with 50-point round numbers and a 10-point offset, process_orders_on_close, one position. Long: bullish bar, previous close <= blue + 10 < close where
blue = floor((close - 10) / 50) x 50, and (blue + 40 - close) >= 1.5 (close - blue) with both positive -> buy at the close, stop = blue, limit = blue + 40; short mirrored (blue' = ceil((close + 10) / 50) x 50, red = blue' - 10, stop = blue', limit = blue' - 40).
The bracket is issued with the entry and works from the next bar. Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "5zL50iGH"


def check():
    df = bars(30000, seed=631, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = df[k] * 5.0
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    lb = np.floor((c - 10.0) / 50.0) * 50.0
    lg, lf = lb + 10.0, lb + 40.0
    sb = np.ceil((c + 10.0) / 50.0) * 50.0
    sr, sf = sb - 10.0, sb - 40.0
    pc = np.r_[np.nan, c[:-1]]
    with np.errstate(invalid="ignore"):
        lrr = ((c - lb) > 0) & ((lf - c) > 0) & ((lf - c) + 1e-8 >= 1.5 * (c - lb))
        srr = ((sb - c) > 0) & ((c - sf) > 0) & ((c - sf) + 1e-8 >= 1.5 * (sb - c))
        buy = (c > o) & (pc <= lg) & (c > lg) & lrr
        sell = (c < o) & (pc >= sr) & (c < sr) & srr
    lev = {}

    def orders(i, pos):
        if pos != 0:
            return []
        if buy[i]:
            lev[i] = (lb[i], lf[i])
            return [("entry", 1)]
        if sell[i]:
            lev[i] = (sb[i], sf[i])
            return [("entry", -1)]
        return []

    stop = lambda i, pos, ep, eb: lev[eb][0] if (eb in lev and eb < i) else None
    tgt = lambda i, pos, ep, eb: lev[eb][1] if (eb in lev and eb < i) else None
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt, on_close=True)
    sym = SymbolInfo.make("OANDA:XAUUSD", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"
