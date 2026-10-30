"""Independent check — AI Triple Confirmation (pXsgrZUz): daily bars, EMA lengths 20 / 60 here (passed to both sides). Fast > slow EMA, RSI14 > 55 and close crossing over the latest confirmed pivot high (5 bars each side, strict) buys; mirror sells with RSI < 45 and a cross under the latest pivot low.
Entries at the next open (reversing), pyramiding 1; every signal (also while already in the trade) sets stop = close -/+ ATR14 and target = close +/- 3 ATR14 for that direction."""
import numpy as np

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "pXsgrZUz"
K, F, SL_ = 5, 20, 60


def check():
    df = bars(9000, seed=18)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ef, es, rsi, atr = np_ema(c, F), np_ema(c, SL_), np_rsi(c, 14), np_atr(h, l, c, 14)
    lh, ll = np.full(n, np.nan), np.full(n, np.nan)
    a = b = np.nan
    for i in range(n):
        if i >= 2 * K:
            m = i - K
            w = h[m - K:m + K + 1]
            if h[m] == w.max() and (w == h[m]).sum() == 1:
                a = h[m]
            w = l[m - K:m + K + 1]
            if l[m] == w.min() and (w == l[m]).sum() == 1:
                b = l[m]
        lh[i], ll[i] = a, b
    with np.errstate(invalid="ignore"):
        buy = (ef > es) & (rsi > 55) & np_cross_over(c, lh)
        sell = (ef < es) & (rsi < 45) & np_cross_under(c, ll)
    lvl = {}

    def orders(i, pos):
        out = []
        if buy[i]:
            out.append(("entry", 1))
            lvl[1] = (c[i] - atr[i], c[i] + atr[i] * 3)
        if sell[i]:
            out.append(("entry", -1))
            lvl[-1] = (c[i] + atr[i], c[i] - atr[i] * 3)
        return out

    def stop(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][0]

    def target(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Fast EMA": F, "Slow EMA": SL_},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
