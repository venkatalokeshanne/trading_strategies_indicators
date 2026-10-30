"""Independent check — Channel Reversion System (XRZCjbFr): daily bars, slippage 0, orders at the signal close (process_orders_on_close), long only. Channel = highest high / lowest low of the previous 50 bars (shifted one bar); buy zone top = low + 25% of the range; trend = close > SMA200.
Flat and trend ok and close <= zone top -> buy at the close; in a trade: close >= mid -> exit, else close < channel low - 1 ATR14 -> exit, else close < SMA200 -> exit (at the bar close)."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "XRZCjbFr"


def check():
    df = bars(9000, seed=123)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    up = np.r_[np.nan, pd.Series(h).rolling(50).max().to_numpy()[:-1]]
    lo = np.r_[np.nan, pd.Series(l).rolling(50).min().to_numpy()[:-1]]
    mid = (up + lo) / 2
    zt = lo + (up - lo) * 25.0 / 100.0
    atr, sma = np_atr(h, l, c, 14), np_sma(c, 200)

    def orders(i, pos):
        out = []
        with np.errstate(invalid="ignore"):
            if pos <= 0 and c[i] > sma[i] and c[i] <= zt[i]:
                out.append(("entry", 1))
            if pos > 0:
                if c[i] >= mid[i] or c[i] < lo[i] - atr[i] or c[i] < sma[i]:
                    out.append(("close", 1))
        return out

    ref = simulate(o, h, l, c, orders, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
