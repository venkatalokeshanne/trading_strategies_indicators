"""Independent check — Albtrader NQ Beast (NHlZr8dq): hourly bars. np_supertrend(3, 10) up (direction < 0) + MACD(12,26,9) crossing over its signal + RSI14 > 30 + close > EMA200 buys; mirror (direction > 0, MACD cross under, RSI < 70,
close < EMA200) sells short; both reverse. While a position is open at a close a bracket (stop 1.2 ATR, target 2 ATR around the entry price) works from the next bar with that close's ATR. A SuperTrend flip against the position closes
at the next open. Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_ema, np_rsi, np_supertrend, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "NHlZr8dq"


def check():
    df = bars(40000, seed=302, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    _, d = np_supertrend(h, l, c, 3.0, 10)
    m = np_ema(c, 12) - np_ema(c, 26)
    sg = np_ema(m, 9)
    rsi, e, atr = np_rsi(c, 14), np_ema(c, 200), np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        lc = (d < 0) & np_cross_over(m, sg) & (rsi > 30) & (c > e)
        sc = (d > 0) & np_cross_under(m, sg) & (rsi < 70) & (c < e)
    poscl = np.zeros(n)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if lc[i]:
            out.append(("entry", 1))
        if sc[i]:
            out.append(("entry", -1))
        if pos > 0 and d[i] > 0:
            out.append(("close", 1))
        if pos < 0 and d[i] < 0:
            out.append(("close", -1))
        return out

    def level(k):
        def fn(i, pos, ep, eb):
            if i == 0 or poscl[i - 1] != pos or np.isnan(atr[i - 1]):
                return None
            return ep - pos * atr[i - 1] * 1.2 if k == 0 else ep + pos * atr[i - 1] * 2.0
        return fn

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
