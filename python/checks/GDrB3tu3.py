"""Independent check — Bollinger Bands Simple Strategy (GDrB3tu3): daily bars, process_orders_on_close, one position. close < lower BB(20, 2) goes long, close > upper goes short, while flat, at the close. While in a position
the stop (5-bar swing low - 1.5 ATR14 for longs, swing high + 1.5 ATR for shorts) and the limit (the SMA20 basis) are re-issued every bar from that bar's values, so bar i works with bar i-1's levels and only if a position existed
at bar i-1's script run. Position size 5% of equity on the pinelib side; margin and slippage off."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "GDrB3tu3"


def check():
    df = bars(6000, seed=905)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    basis = np_sma(c, 20)
    dev = 2.0 * pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    up, lo = basis + dev, basis - dev
    atr = np_atr(h, l, c, 14)
    sw_lo = pd.Series(l).rolling(5, min_periods=5).min().to_numpy()
    sw_hi = pd.Series(h).rolling(5, min_periods=5).max().to_numpy()
    with np.errstate(invalid="ignore"):
        bs, ss = c < lo, c > up
    poscl = np.zeros(n)

    def orders(i, pos):
        poscl[i] = pos
        if pos != 0:
            return []
        return [("entry", 1)] if bs[i] else ([("entry", -1)] if ss[i] else [])

    def stop(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0:
            return None
        return sw_lo[i - 1] - atr[i - 1] * 1.5 if pos > 0 else sw_hi[i - 1] + atr[i - 1] * 1.5

    def target(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0:
            return None
        return basis[i - 1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
