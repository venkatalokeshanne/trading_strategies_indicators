"""Independent check — EMA DMI MACD RSI (z39XLJR2): 5-min New York bars. Eleven conditions (EMA stack, EMA200, MACD vs signal, RSI 55/45,
+DI/-DI, ADX>20, volume>SMA20, close vs the hourly EMA50). Hourly EMA50 is built from plain-pandas 60-minute blocks and shown with
lookahead off (last chart bar of the hour = that hour; earlier bars = previous hour). Exits are unconditional: bar i works with
bar i-1's close -/+ 1.5 ATR stop and +/- 3 ATR target (also on the fill bar)."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_dmi, np_ema, np_periods, np_rsi, np_security_lookahead_off, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "z39XLJR2"


def check():
    df = bars(40000, seed=105, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    e5, e13, e26, e200 = (np_ema(c, n) for n in (5, 13, 26, 200))
    rsi, atr = np_rsi(c, 14), np_atr(h, l, c, 14)
    macd = np_ema(c, 12) - np_ema(c, 26)
    sig = np_ema(macd, 9)
    pdi, mdi, adx = np_dmi(h, l, c, 14)
    hv = v > np_sma(v, 20)
    pid, last_of = np_periods(df, 60)
    hc = pd.Series(c).groupby(pid).last().to_numpy()
    htf = np_security_lookahead_off(np_ema(hc, 50), pid, last_of)
    with np.errstate(invalid="ignore"):
        buy = (e5 > e13) & (e13 > e26) & (c > e200) & (macd > sig) & (rsi > 55) & (pdi > mdi) & (adx > 20) & hv & (c > htf)
        sell = (e5 < e13) & (e13 < e26) & (c < e200) & (macd < sig) & (rsi < 45) & (mdi > pdi) & (adx > 20) & hv & (c < htf)

    def stop(i, pos, ep, eb):
        return None if i == 0 else (c[i - 1] - atr[i - 1] * 1.5 if pos > 0 else c[i - 1] + atr[i - 1] * 1.5)

    def target(i, pos, ep, eb):
        return None if i == 0 else (c[i - 1] + atr[i - 1] * 3 if pos > 0 else c[i - 1] - atr[i - 1] * 3)

    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if buy[i] else []) + ([("entry", -1)] if sell[i] else []),
                   stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
