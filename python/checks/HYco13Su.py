"""Independent check — Turtle Trading with ATR Stop + Pyramiding (HYco13Su): daily bars, process_orders_on_close, long only, trade list (lot sizes do not change entries / exits). Entry: close > highest high of the previous 20 bars
(and > SMA200) while flat. The script's reset block runs after the entry on the entry bar (position still 0 at script time), clearing the last-entry price, so no pyramid add is ever possible. The ATR stop starts at close - 2 ATR20 on
the entry bar (then reset to na by that same block), is rebuilt at the next script run as max(old, close - 2 ATR) (na -> new), and is issued as exit stop while long (works from the next bar). The exit: close below the previous 10
bars' lowest low or below the stop, edge-triggered (a raw signal that was already true on the previous bar does not fire again), closes the position at the close. Position size 25% of equity on the pinelib side; margin, slippage off."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "HYco13Su"


def check():
    df = bars(6000, seed=147)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ma = np_sma(c, 200)
    eh = pd.Series(np.r_[np.nan, h[:-1]]).rolling(20, min_periods=20).max().to_numpy()
    el = pd.Series(np.r_[np.nan, l[:-1]]).rolling(10, min_periods=10).min().to_numpy()
    atr = np_atr(h, l, c, 20)
    with np.errstate(invalid="ignore"):
        raw_buy = (c > eh) & (c > ma)
    S = dict(stop=np.nan, prev=False)
    stop_arr = np.full(n, np.nan)
    poscl = np.zeros(n)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if raw_buy[i] and pos == 0:
            out.append(("entry", 1))
            S["stop"] = c[i] - atr[i] * 2.0
        if pos == 0:
            S["stop"] = np.nan
        if pos > 0:
            ns = c[i] - atr[i] * 2.0
            S["stop"] = ns if np.isnan(S["stop"]) else max(S["stop"], ns)
        with np.errstate(invalid="ignore"):
            raw = pos > 0 and (c[i] < el[i] or c[i] < S["stop"])
        sell = raw and not S["prev"]
        S["prev"] = raw
        if pos > 0 and not np.isnan(S["stop"]):
            stop_arr[i] = S["stop"]
        if sell:
            out.append(("close", 1))
        return out

    def stop(i, pos, ep, eb):
        if i == 0 or np.isnan(stop_arr[i - 1]) or poscl[i - 1] <= 0:
            return None
        return stop_arr[i - 1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
