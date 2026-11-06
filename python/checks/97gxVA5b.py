"""Independent check — Compression Breakout System (97gxVA5b): daily bars, process_orders_on_close, long only, trade list only. Width = 2 x (2 x stdev20) / SMA20 x 100; its percent rank = share of the previous 126 widths <= the
current one; squeeze = rank < 25, and one occurred in the last 5 bars (including this one). Buy when flat, close > the previous 20 bars' highest high, volume > SMA20(volume), close > SMA200. The script then keeps a
high-water mark of the closes since entry and closes at the bar close when close < max(entry close - 2 ATR22, hwm - 3 ATR22) (the entry-bar ATR fixes the first term; ATR is the current bar's for the trail). Margin and slippage off."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "97gxVA5b"


def check():
    df = bars(8000, seed=616)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    basis = np_sma(c, 20)
    dev = pd.Series(c).rolling(20).std(ddof=0).to_numpy() * 2.0
    w = 2.0 * dev / basis * 100.0
    rank = np.full(n, np.nan)
    for i in range(126, n):
        if not np.isnan(w[i]):
            prev = w[i - 126:i]
            rank[i] = 100.0 * np.sum(prev <= w[i]) / 126
    with np.errstate(invalid="ignore"):
        sq = (rank < 25.0).astype(int)
    recent = pd.Series(sq).rolling(5, min_periods=5).sum().to_numpy() > 0
    brk = np.r_[np.nan, pd.Series(h).rolling(20, min_periods=20).max().to_numpy()[:-1]]
    vok = v > np_sma(v, 20)
    atr = np_atr(h, l, c, 22)
    sma = np_sma(c, 200)
    with np.errstate(invalid="ignore"):
        buy = recent & (c > brk) & vok & (c > sma)
    S = dict(stop=np.nan, hwm=np.nan)

    def orders(i, pos):
        out = []
        if buy[i] and pos == 0:
            out.append(("entry", 1))
            S["stop"] = c[i] - atr[i] * 2.0
            S["hwm"] = c[i]
        if pos > 0:
            S["hwm"] = max(S["hwm"], c[i])
            lvl = max(S["stop"], S["hwm"] - atr[i] * 3.0)
            if c[i] < lvl:
                out.append(("close", 1))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "default_qty_value": 5}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
