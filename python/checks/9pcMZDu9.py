"""Independent check — Serhan3 WMA + ADX + Trailing + Date Filter (9pcMZDu9): daily bars from 2015 (From Year passed as 2015, so the window starts 2015-01-01 00:00 New York time = 05:00 UTC). WMA(11) crossing WMA(28) with the
close beyond both and ADX(18) > 24 reverses; while a position is open at a close the trailing exit (activation 0.8 % of that close in ticks of 0.01, offset 0) is issued and works from the next bar with that previous close.
Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_adx, np_cross_over, np_cross_under, np_wma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "9pcMZDu9"
TICK = 0.01


def check():
    df = bars(6000, seed=252)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    t = df["time"].to_numpy()
    start = int(pd.Timestamp(year=2015, month=1, day=1, tz="America/New_York").tz_convert("UTC").value // 1_000_000)
    inr = t >= start
    f, s, adx = np_wma(c, 11), np_wma(c, 28), np_adx(h, l, c, 18)
    with np.errstate(invalid="ignore"):
        lc = np_cross_over(f, s) & (c > f) & (c > s) & (adx > 24) & inr
        sc = np_cross_under(f, s) & (c < f) & (c < s) & (adx > 24) & inr
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if lc[i] else []) + ([("entry", -1)] if sc[i] else []),
                   trail=lambda i, pos, ep, eb: None if eb >= i else (c[i - 1] * 0.008 / TICK, 0), tick=TICK)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"From Year": 2015},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
