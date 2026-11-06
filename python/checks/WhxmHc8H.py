"""Independent check — 3Commas grid bot (WhxmHc8H): 1h continuous bars, orders at the bar close (process_orders_on_close), slippage 0, grid bounds 130 / 70 with 23 levels (Geometric) and the backtest window widened to the whole sample (passed to both sides). Custom per-slot reference (the shared brokers close all lots of a direction):
level i = 130 * (70/130)^(i/22); at each bar close, for levels 1..22 in order: a slot not held whose previous close was above the level and whose close is at or below it is bought at the close; a slot held at the START of the iteration whose previous close was below the level above (i-1) and whose close is at or above it is sold at the close. Trades are slots, listed in the order they close."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion
from pinelib import SymbolInfo

TV_ID = "WhxmHc8H"
HI, LO, N = 130.0, 70.0, 23


def check():
    df = bars(12000, seed=420, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    lv = [HI * (LO / HI) ** (i / (N - 1)) for i in range(N)]
    held = {}
    trades = []
    for i in range(n):
        pc = c[i - 1] if i else c[i]
        for k in range(1, N):
            owned = k in held
            if (not owned) and pc > lv[k] and c[i] <= lv[k]:
                held[k] = (i, c[i])
            if owned and pc < lv[k - 1] and c[i] >= lv[k - 1]:
                b, p = held.pop(k)
                trades.append((1, b, p, i, c[i]))
    t0 = int(pd.Timestamp("2015-01-01", tz="UTC").value // 1_000_000)
    t1 = int(pd.Timestamp("2099-01-01", tz="UTC").value // 1_000_000)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", params={"High Price": HI, "Low Price": LO, "Grid Levels": N, "From": t0, "To": t1},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), trades)
    return ok and len(trades) > 5, f"{detail} (need >5 trades, got {len(trades)})"
