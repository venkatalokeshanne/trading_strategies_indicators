"""Independent check — Market Leader PRO (NjXdoUmw): hourly bars. np_supertrend(3, 10) direction change < 0 (flip to up; na on the first bar is false) with close > EMA200, RSI14 > 50, close above the previous 20-bar highest high
and volume > SMA20 goes long when flat (mirror short). A change > 0 closes a long, < 0 closes a short at the next open. While a position is open at a close: 1.2 % target / 0.6 % stop around the entry price, working from the
next bar. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, np_rsi, np_sma, np_supertrend, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "NjXdoUmw"


def check():
    df = bars(40000, seed=272, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    _, d = np_supertrend(h, l, c, 3.0, 10)
    chg = np.r_[np.nan, np.diff(d)]
    e, rsi, vm = np_ema(c, 200), np_rsi(c, 14), np_sma(v, 20)
    hh = pd.Series(h).shift(1).rolling(20).max().to_numpy()
    ll = pd.Series(l).shift(1).rolling(20).min().to_numpy()
    with np.errstate(invalid="ignore"):
        ls = (c > e) & (rsi > 50) & (chg < 0) & (c > hh) & (v > vm)
        ss = (c < e) & (rsi < 50) & (chg > 0) & (c < ll) & (v > vm)

    def orders(i, pos):
        out = []
        if ls[i] and pos == 0:
            out.append(("entry", 1))
        if ss[i] and pos == 0:
            out.append(("entry", -1))
        if chg[i] > 0 and pos > 0:
            out.append(("close", 1))
        if chg[i] < 0 and pos < 0:
            out.append(("close", -1))
        return out

    ref = simulate(o, h, l, c, orders,
                   stop=lambda i, pos, ep, eb: None if eb >= i else ep * (1 - 0.006 * pos),
                   target=lambda i, pos, ep, eb: None if eb >= i else ep * (1 + 0.012 * pos))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
