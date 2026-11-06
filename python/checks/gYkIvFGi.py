"""Independent check — Momentum Breakout (gYkIvFGi): 4-hour bars, one position, market entries at the next open (an opposite signal reverses; a same-side signal is ignored but still re-issues the bracket, which replaces the working one). Long: close crosses over SMA200 while MACD line > 0 and the stochastic RSI %K
(SMA3 of stoch(RSI14, 14); na when the window is flat) > 80; short: cross under, MACD < 0, %K < 20. A swing high / low = latest confirmed pivot (10 bars each side, strict) must exist; long TP = swing high x 1.001 (> close), SL = swing low x 0.999 (< close); short TP = swing low x 0.999 (< close), SL = swing high x 1.001 (> close).
The bracket that works on bar i is the latest one issued for that side up to bar i-1. Variants: default and wider thresholds (70 / 30). Slippage / margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, np_rsi, np_sma, np_stoch, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "gYkIvFGi"
K = 10


def one(df, params, bull, bear):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sma = np_sma(c, 200)
    macd = np_ema(c, 12) - np_ema(c, 26)
    rsi = np_rsi(c, 14)
    k = np_sma(np_stoch(rsi, rsi, rsi, 14), 3)
    ph, pl = np.full(n, np.nan), np.full(n, np.nan)
    for i in range(2 * K, n):
        j = i - K
        if h[j] > h[j - K:j].max() and h[j] > h[j + 1:i + 1].max():
            ph[i] = h[j]
        if l[j] < l[j - K:j].min() and l[j] < l[j + 1:i + 1].min():
            pl[i] = l[j]
    with np.errstate(invalid="ignore"):
        lc = np_cross_over(c, sma) & (macd > 0) & (k > bull)
        sc = np_cross_under(c, sma) & (macd < 0) & (k < bear)
    S = dict(sh=np.nan, sl=np.nan, L=None, S=None)

    def orders(i, pos):
        out = []
        if not np.isnan(ph[i]):
            S["sh"] = ph[i]
        if not np.isnan(pl[i]):
            S["sl"] = pl[i]
        if lc[i] and not np.isnan(S["sh"]) and not np.isnan(S["sl"]):
            tp, sl = S["sh"] * 1.001, S["sl"] * 0.999
            if tp > c[i] and sl < c[i]:
                out.append(("entry", 1))
                S["L"] = (sl, tp)
        if sc[i] and not np.isnan(S["sh"]) and not np.isnan(S["sl"]):
            tp, sl = S["sl"] * 0.999, S["sh"] * 1.001
            if tp < c[i] and sl > c[i]:
                out.append(("entry", -1))
                S["S"] = (sl, tp)
        return out

    stop = lambda i, pos, ep, eb: (S["L"] if pos > 0 else S["S"])[0] if (S["L"] if pos > 0 else S["S"]) else None
    tgt = lambda i, pos, ep, eb: (S["L"] if pos > 0 else S["S"])[1] if (S["L"] if pos > 0 else S["S"]) else None
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="240", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(60000, seed=711, freq="4h")
    msgs, allok = [], True
    for params, b, s in (({}, 80, 20), ({"Bull Threshold (Long  Entry)": 55, "Bear Threshold (Short Entry)": 45}, 55, 45)):
        ok, m = one(df, params, b, s)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
