"""Independent check — BTC Long Only by Soran (sYMa3n2C): daily bars, long only, 1 unit. Signal on bar i from bar i-1: low < lower BB(20, 2), RSI14 < 35, bullish close, volume > 1.3 x SMA20(volume) (all of bar i-1's own values), flat.
Entry at the next open; limit = bar i-1's upper band, stop = close(i) x 0.981, both fixed at the signal bar (the exit order is placed together with the entry, so it works on the fill bar). Margin, commission and slippage off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "sYMa3n2C"


def check():
    df = bars(8000, seed=584)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    basis = np_sma(c, 20)
    dev = 2.0 * pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    up, lo = basis + dev, basis - dev
    rsi = np_rsi(c, 14)
    vm = np_sma(v, 20)
    sh = lambda x: np.r_[np.nan, x[:-1]]
    with np.errstate(invalid="ignore"):
        sig = (sh(l) < sh(lo)) & (sh(rsi) < 35) & (sh(c) > sh(o)) & (sh(v) > sh(vm) * 1.3)
    lv = {}

    def orders(i, pos):
        if pos == 0 and sig[i]:
            lv["v"] = (c[i] * (1 - 0.019), sh(up)[i])
            return [("entry", 1)]
        return []

    def stop(i, pos, ep, eb):
        return lv["v"][0] if "v" in lv else None

    def target(i, pos, ep, eb):
        return lv["v"][1] if "v" in lv else None

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "commission_value": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
