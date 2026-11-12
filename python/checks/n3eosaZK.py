"""Independent check — Rudy Breakout Momentum v2 (n3eosaZK): daily bars, long only. high >= the highest high of the 126 bars before this one, EMA21 > EMA50 and 40 < RSI14 < 80 buys when flat. While a position is open at a close:
target +15 % / stop -8 % around the entry price, working from the next bar. Close < EMA21 with the previous close >= the previous EMA21 closes at the next open. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "n3eosaZK"


def check():
    df = bars(8000, seed=282)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    e21, e50, rsi = np_ema(c, 21), np_ema(c, 50), np_rsi(c, 14)
    h126 = pd.Series(h).shift(1).rolling(126).max().to_numpy()
    c1, e1 = np.r_[np.nan, c[:-1]], np.r_[np.nan, e21[:-1]]
    with np.errstate(invalid="ignore"):
        buy = (h >= h126) & (e21 > e50) & (rsi < 80) & (rsi > 40)
        tb = (c < e21) & (c1 >= e1)

    def orders(i, pos):
        out = []
        if buy[i] and pos == 0:
            out.append(("entry", 1))
        if tb[i] and pos > 0:
            out.append(("close", 1))
        return out

    ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: None if eb >= i else ep * 0.92,
                   target=lambda i, pos, ep, eb: None if eb >= i else ep * 1.15)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
