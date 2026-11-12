"""Independent check — Momentum Exhaustion Breakout (gqaZYhUN): daily bars, single position (trade list only; the risk-sized quantity does not change entries / exits). Breakout = high > the previous 20 bars' highest high
and volume > 1.5 x SMA20(volume). Long: EMA20 > EMA50, RSI14 rising over 5 bars and > 55. Fade short: breakout outside an uptrend with RSI below its prior 20-bar peak (excluding this bar) or RSI falling. Only when flat.
While in a position the stop (avg -/+ 1.5 ATR) and an ATR trailing stop (points = offset = 1.5 ATR in ticks) from the previous bar's close work from the next bar. Margin, slippage off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "gqaZYhUN"


def check():
    df = bars(5000, seed=733)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    ef, es = np_ema(c, 20), np_ema(c, 50)
    h1 = np.r_[np.nan, h[:-1]]
    ph = pd.Series(h1).rolling(20, min_periods=20).max().to_numpy()
    rsi = np_rsi(c, 14)
    roc = rsi - np.r_[np.full(5, np.nan), rsi[:-5]]
    r1 = np.r_[np.nan, rsi[:-1]]
    pk = pd.Series(r1).rolling(20, min_periods=20).max().to_numpy()
    va = np_sma(v, 20)
    atr = np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        up = ef > es
        brk = (h > ph) & (v > va * 1.5)
        ls = brk & up & (roc > 0) & (rsi > 55)
        fs = brk & ~up & ((rsi < pk) | (roc < 0))
        ok_atr = atr * 1.5 > 0
    poscl = np.zeros(n)

    def orders(i, pos):
        poscl[i] = pos
        if pos == 0 and ok_atr[i]:
            if ls[i]:
                return [("entry", 1)]
            if fs[i]:
                return [("entry", -1)]
        return []

    def stop(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0:
            return None
        return ep - atr[i - 1] * 1.5 if pos > 0 else ep + atr[i - 1] * 1.5

    def trail(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0:
            return None
        t = atr[i - 1] * 1.5                      # the script passes atr * mult as a tick count
        return (t, t)

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, trail=trail, tick=0.01)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
