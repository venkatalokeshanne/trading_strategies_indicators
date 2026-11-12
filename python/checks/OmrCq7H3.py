"""Independent check — TRADLEWARE-DCA (OmrCq7H3): daily bars from 2015 (the 2018-01-01 New York start leaves the window inside the sample), slippage 0, orders at the bar close (process_orders_on_close), pyramiding 500, one unit per buy (indep.simulate_pyr). From the first bar inside the window (and not the last bar) buy every 30 bars (the first buy counts
as bar 0 of the schedule via lastBuy == 0), as long as 100 more still fits in the 10,000 capital (the schedule advances even when the cap blocks the buy). The last bar closes everything."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion, simulate_pyr
from pinelib import SymbolInfo

TV_ID = "OmrCq7H3"


def check():
    df = bars(9000, seed=4)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    t0 = pd.Timestamp(year=2018, month=1, day=1, tz="America/New_York").value // 1_000_000
    inr = df["time"].to_numpy() >= t0
    s = dict(last=0, inv=0.0)

    def orders(i, pos):
        out = []
        if inr[i] and i != n - 1 and (s["last"] == 0 or i >= s["last"] + 30):
            s["last"] = i
            if s["inv"] + 100.0 <= 10000.0:
                out.append(("entry", 1))
                s["inv"] += 100.0
        if i == n - 1:
            out.append(("close_all",))
        return out

    ref = simulate_pyr(o, h, l, c, orders, pyramiding=500, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
