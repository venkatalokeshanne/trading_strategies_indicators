"""Independent check — Swing Trading Manual v1 (SaSpHWMm): hourly bars, long only. Daily close > daily EMA20 and EMA50 and daily MACD(12,26,9) histogram > 0 (plain-pandas daily blocks from 09:30, lookahead off); chart close <= EMA20 or
<= SMA20; RSI14 > 45; chart MACD histogram > 0 or MACD > signal. Buys when flat; entry + exit (stop = close - 1.5 ATR14, limit = close + 2 * distance) are issued on the signal bar, so the bracket works from the fill bar.
Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_periods, np_rsi, np_security_lookahead_off, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "SaSpHWMm"


def check():
    df = bars(40000, seed=289, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    pid, last_of = np_periods(df, 1440)
    dc = pd.Series(c).groupby(pid).last().to_numpy()
    dm = np_ema(dc, 12) - np_ema(dc, 26)
    dh = dm - np_ema(dm, 9)
    d_close, d20, d50, dhist = (np_security_lookahead_off(x, pid, last_of) for x in (dc, np_ema(dc, 20), np_ema(dc, 50), dh))
    e20, mid, rsi, atr = np_ema(c, 20), np_sma(c, 20), np_rsi(c, 14), np_atr(h, l, c, 14)
    m = np_ema(c, 12) - np_ema(c, 26)
    sg = np_ema(m, 9)
    with np.errstate(invalid="ignore"):
        bull = (d_close > d20) & (d_close > d50) & (dhist > 0)
        sig = bull & ((c <= e20) | (c <= mid)) & (rsi > 45) & (((m - sg) > 0) | (m > sg))
    lvl = [np.nan, np.nan]

    def orders(i, pos):
        if sig[i] and pos == 0:
            stop = c[i] - atr[i] * 1.5
            lvl[0], lvl[1] = stop, c[i] + (c[i] - stop) * 2.0
            return [("entry", 1)]
        return []

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: lvl[0], target=lambda i, pos, ep, eb: lvl[1])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
