"""Independent check — TRADLEWARE-HODL (wgsvzsT3): daily bars. Buy at the open after the first bar on/after 2018-01-01 (a single trade: closedtrades == 0), close_all issued on
the second to last bar so the exit fills at the open of the last bar. Slippage (3 ticks) is 0 on both sides; margin off (99.95 % of equity)."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "wgsvzsT3"


def check():
    df = bars(3500, seed=167)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    t = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    start = pd.Timestamp("2018-01-01", tz="America/New_York")
    closed = [0]

    def orders(i, pos):
        out = []
        if t.iloc[i] >= start and len(closed) == 0 and pos == 0:
            out.append(("entry", 1))
        if i >= n - 2 and pos != 0:
            out.append(("close", pos))
        return out

    # closedtrades == 0 becomes false only once a trade has CLOSED; before that the entry is re-issued each flat bar (it fills next open)
    log = []
    closed = log
    ref = simulate(o, h, l, c, orders, log=log)
    sym = SymbolInfo.make("AMEX:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) >= 1, f"{detail} (need >=1 trade, got {len(ref)})"
