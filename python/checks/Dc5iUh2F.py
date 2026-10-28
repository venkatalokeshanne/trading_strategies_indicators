"""Independent check — 3Commas static grid (Dc5iUh2F): 1h continuous bars, slippage 0, bounds 130 / 70 with 23 levels, Trailing Up ON (passed to both sides; shifts the grid by 50% of its range when the close exceeds the high by 3%), window widened to the whole sample. Custom per-slot reference with next-open fills:
level k = lo * (hi/lo)^(k/22) (recomputed after a shift); after a bar closes: for k = 0..21 a held slot is sold when close >= level[k+1] and the previous close was below it; then for k = 0..22 a free slot is bought when close <= level[k] and the previous close was above it (the sold slot's flag is already cleared); both fill at the next bar's open in that order.
Trades are slots, listed in the order they close (sells fill before the same bar's buys)."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion
from pinelib import SymbolInfo

TV_ID = "Dc5iUh2F"
HI, LO, N = 130.0, 70.0, 23


def check():
    df = bars(12000, seed=430, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    hi, lo = HI, LO

    def levels():
        return [lo * (hi / lo) ** (k / (N - 1.0)) for k in range(N)]

    lv = levels()
    filled = [False] * N
    held = {}
    pend = []
    trades = []
    for i in range(n):
        for kind, k in pend:
            if kind == "sell":
                b, p = held.pop(k)
                trades.append((1, b, p, i, o[i]))
            else:
                held[k] = (i, o[i])
        pend = []
        if c[i] > hi * 1.03:
            rng = hi - lo
            hi, lo = hi + rng * 0.5, lo + rng * 0.5
            lv = levels()
        if i > 0:
            for k in range(0, N - 1):
                if filled[k] and c[i] >= lv[k + 1] and c[i - 1] < lv[k + 1]:
                    pend.append(("sell", k))
                    filled[k] = False
            for k in range(0, N):
                if (not filled[k]) and c[i] <= lv[k] and c[i - 1] > lv[k]:
                    pend.append(("buy", k))
                    filled[k] = True
    t0 = int(pd.Timestamp("2015-01-01", tz="UTC").value // 1_000_000)
    t1 = int(pd.Timestamp("2099-01-01", tz="UTC").value // 1_000_000)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60",
                                        params={"Grid High Price": HI, "Grid Low Price": LO, "Grid Levels": N, "Trailing Up — shift grid when price exceeds High": True, "Start": t0, "End": t1},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), trades)
    return ok and len(trades) > 5, f"{detail} (need >5 trades, got {len(trades)})"
