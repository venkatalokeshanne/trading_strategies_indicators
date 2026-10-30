"""Independent check — VWAP Squeeze Reclaim LONG ONLY (1UtA1u3v): 5-min New York bars. Long when flat: Supertrend(1.5, 21) up, close > session VWAP, MACD(12,26,9) above its signal and above 0, RSI14 < 60, +DI > -DI and
before 15:00 exchange time. Closes at the next open when close < VWAP, MACD < signal, or the Supertrend turns down. (The np_supertrend reference is the textbook Pine implementation.)"""
import numpy as np
import pandas as pd

from indep import bars, compare, np_dmi, np_ema, np_rsi, np_supertrend, np_vwap, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "1UtA1u3v"


def check():
    df = bars(40000, seed=242, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    early = (ny.dt.hour.to_numpy() < 15)
    vw = np_vwap(df, c)
    m = np_ema(c, 12) - np_ema(c, 26)
    sg = np_ema(m, 9)
    rsi = np_rsi(c, 14)
    pdi, mdi, _ = np_dmi(h, l, c, 14)
    _, d = np_supertrend(h, l, c, 1.5, 21)
    with np.errstate(invalid="ignore"):
        buy = (d < 0) & (c > vw) & (m > sg) & early & (m > 0) & (rsi < 60) & (pdi > mdi)
        sell = (c < vw) | (m < sg) | (d > 0)
        # crossunder(close, vwap) implies close < vwap, already covered by the (c < vw) term
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if buy[i] and pos == 0 else []) + ([("close", 1)] if sell[i] and pos > 0 else []))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
