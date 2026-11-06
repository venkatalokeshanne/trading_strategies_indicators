"""Independent check — Nifty 45m 200 EMA + RSI 50 cross (IiMQHjLW): 45-min bars. Long: close > EMA200, RSI14 crosses over 50, ATR14 > SMA20(ATR14); short mirrored; flat or opposite required; exits when the close
crosses EMA50 against the position. v6 short-circuits the `and` chain: ta.crossover runs only while close > EMA200 (crossunder while close < EMA200) and its previous value is the last bar it ran on (LESSONS P4/P5).
Margin off on the pinelib side (100 % of equity sizing)."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "IiMQHjLW"


def check():
    df = bars(20000, seed=204, freq="45min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    e200, e50, rsi, atr = np_ema(c, 200), np_ema(c, 50), np_rsi(c, 14), np_atr(h, l, c, 14)
    asma = np_sma(atr, 20)
    with np.errstate(invalid="ignore"):
        flt = atr > asma
        above, below = c > e200, c < e200
        xl = np.zeros(n, bool)
        xs = np.zeros(n, bool)
    pl = ps = np.nan                                    # rsi at the last bar each cross call ran
    for i in range(n):
        if above[i]:
            xl[i] = bool(rsi[i] > 50 and pl <= 50)
            pl = rsi[i]
        if below[i]:
            xs[i] = bool(rsi[i] < 50 and ps >= 50)
            ps = rsi[i]
    lc, sc = xl & flt, xs & flt
    with np.errstate(invalid="ignore"):
        exl, exs = c < e50, c > e50

    def orders(i, pos):
        out = []
        if lc[i] and pos <= 0:
            out.append(("entry", 1))
        if sc[i] and pos >= 0:
            out.append(("entry", -1))
        if pos > 0 and exl[i]:
            out.append(("close", 1))
        if pos < 0 and exs[i]:
            out.append(("close", -1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="45", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
