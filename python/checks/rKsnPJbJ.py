"""Independent check — Fib Confluence Scanner (rKsnPJbJ): daily bars, one position at a time, trade list only. For lookbacks 20 / 50 / 100 the levels hi - r x (hi - lo), r in {0.236, 0.382, 0.5, 0.618, 0.786} (hi / lo = rolling
high / low including the current bar); count the levels with |close - level| / close <= 0.5%; count >= 1 = confluence. Long when close > EMA50, short when close < EMA50, only when flat. Stop 1.5% / target 3.0% around the entry
price issued while in a position (work from the next bar). Position size 5% of equity on the pinelib side; margin and slippage off."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "rKsnPJbJ"


def check():
    df = bars(6000, seed=704)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    cnt = np.zeros(n, int)
    for ln in (20, 50, 100):
        hi = pd.Series(h).rolling(ln, min_periods=ln).max().to_numpy()
        lo = pd.Series(l).rolling(ln, min_periods=ln).min().to_numpy()
        for r in (0.236, 0.382, 0.5, 0.618, 0.786):
            lvl = hi - r * (hi - lo)
            with np.errstate(invalid="ignore"):
                cnt += (np.abs(c - lvl) / c <= 0.005).astype(int)
    ema = np_ema(c, 50)
    with np.errstate(invalid="ignore"):
        conf = cnt >= 1
        ls, ss = conf & (c > ema), conf & (c < ema)
    poscl = np.zeros(n)

    def orders(i, pos):
        poscl[i] = pos
        if pos != 0:
            return []
        return [("entry", 1)] if ls[i] else ([("entry", -1)] if ss[i] else [])

    def stop(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0:
            return None
        return ep * 0.985 if pos > 0 else ep * 1.015

    def target(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0:
            return None
        return ep * 1.03 if pos > 0 else ep * 0.97

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "default_qty_value": 5}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
