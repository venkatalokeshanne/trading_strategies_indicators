"""Independent check — 3-strategy switch (MoL1SwLE): hourly bars, long only. Range: ADX14 < 25 with the close inside Bollinger(20, 2), RSI14 < 35, close <= lower * 1.01, volume > 1.2 SMA20. Trend: close > EMA50 > EMA200, ADX > 25,
EMA50 crossing over EMA200, RSI > 50, close > basis. Breakout: volume > 1.8 SMA20, close crossing over the upper band, ADX > 20, RSI > 50, previous close under the previous upper band. Any one buys when flat. While a position is open at
a close: stop = entry - 1.5 ATR, target = entry + 2.5 * 1.5 ATR (that close's ATR), working from the next bar. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_adx, np_atr, np_cross_over, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "MoL1SwLE"


def check():
    df = bars(60000, seed=265, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    rsi, adx, atr = np_rsi(c, 14), np_adx(h, l, c, 14), np_atr(h, l, c, 14)
    mid = np_sma(c, 20)
    sd = pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    up, lo = mid + 2 * sd, mid - 2 * sd
    vm = np_sma(v, 20)
    e50, e200 = np_ema(c, 50), np_ema(c, 200)
    c1, up1 = np.r_[np.nan, c[:-1]], np.r_[np.nan, up[:-1]]
    with np.errstate(invalid="ignore"):
        ranging = (adx < 25) & (c > lo) & (c < up)
        trending = (adx > 25) & (c > e50) & (e50 > e200)
        breakout = (v > vm * 1.8) & np_cross_over(c, up) & (adx > 20)
        rl = ranging & (rsi < 35) & (c <= lo * 1.01) & (v > vm * 1.2)
        tl = trending & np_cross_over(e50, e200) & (rsi > 50) & (c > mid)
        bl = breakout & (rsi > 50) & (c1 < up1)
        sig = rl | tl | bl
    poscl, atr_cl = np.zeros(n), atr

    def orders(i, pos):
        poscl[i] = pos
        return [("entry", 1)] if sig[i] and pos == 0 else []

    def level(k):
        def fn(i, pos, ep, eb):
            if i == 0 or poscl[i - 1] <= 0 or np.isnan(atr[i - 1]):
                return None
            return ep - atr[i - 1] * 1.5 if k == 0 else ep + atr[i - 1] * 1.5 * 2.5
        return fn

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
