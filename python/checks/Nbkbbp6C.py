"""Independent check — Rabiah6X pullback (Nbkbbp6C): daily bars, long only. Close > SMA200, hand-written ADX(14) (textbook Wilder DI/ADX, the np_adx reference), close crossing back above EMA21 (crossover, or close > EMA21 with
close[1] <= EMA21[1] — the same condition for continuous data) and 45 <= RSI14 <= 70 enter (repeats ignored). While a position is open at a close, stop = close - 1.8 ATR and limit = close + 1.2 ATR are issued from that close, so
bar i works with bar i-1's levels and none on a fill bar. Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_adx, np_atr, np_cross_over, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "Nbkbbp6C"


def check():
    df = bars(8000, seed=237)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    macro, sm = np_sma(c, 200), np_ema(c, 21)
    adx, rsi, atr = np_adx(h, l, c, 14), np_rsi(c, 14), np_atr(h, l, c, 14)
    sm1, c1 = np.r_[np.nan, sm[:-1]], np.r_[np.nan, c[:-1]]
    with np.errstate(invalid="ignore"):
        trig = np_cross_over(c, sm) | ((c > sm) & (c1 <= sm1))
        sig = (c > macro) & (adx > 20) & trig & (rsi >= 45) & (rsi <= 70)
    poscl = np.zeros(n)

    def orders(i, pos):
        poscl[i] = pos
        return [("entry", 1)] if sig[i] else []

    def level(k):
        return lambda i, pos, ep, eb: (None if i == 0 or poscl[i - 1] <= 0 or np.isnan(atr[i - 1])
                                       else (c[i - 1] - atr[i - 1] * 1.8 if k == 0 else c[i - 1] + atr[i - 1] * 1.2))

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
