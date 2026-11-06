"""Independent check — TASC Ag Selling Model (VFzCk3HX): daily bars, shorts only, pyramiding 3 (indep.simulate_pyr, 1 unit per trade; slippage off). Months are New York calendar months of the bar's open time (the daily bars
open at 00:00 UTC = previous evening in New York). Harvest month 11 starts a new crop year (selling off, counter reset); selling switches on again in month 2 (first bar of that month). While on, a high >= SMA40 + 2.5 ATR20
sells short ("First sale" when nothing is open, else a "Sell" once dSince >= 30 bars, counted only while trades are open); while off every bar closes everything at the next open when something is open."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_sma, run_conversion, simulate_pyr
from pinelib import SymbolInfo

TV_ID = "VFzCk3HX"


def check():
    df = bars(3500, seed=270)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    month = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York").dt.month.to_numpy()
    sell = np_sma(c, 40) + np_atr(h, l, c, 20) * 2.5
    active, dsince = False, 0

    def orders(i, pos):
        nonlocal active, dsince
        count = -pos
        if count > 0:
            dsince += 1
        harvest = month[i] == 11
        prev_harvest = bool(month[i - 1] == 11) if i else False
        pm = month[i - 1] if i else -1
        out = []
        if harvest and not prev_harvest:
            active, dsince = False, 0
        if month[i] == 2 and pm != 2:
            active = True
        with np.errstate(invalid="ignore"):
            if active and h[i] >= sell[i]:
                if count == 0:
                    out.append(("entry", -1)); dsince = 0
                elif dsince >= 30:
                    out.append(("entry", -1)); dsince = 0
        if not active and count > 0:
            out.append(("close_all",))
        return out

    ref = simulate_pyr(o, h, l, c, orders, pyramiding=3)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    res = run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"slippage": 0, "margin_long": 0, "margin_short": 0})
    ok, detail = compare(res, ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
