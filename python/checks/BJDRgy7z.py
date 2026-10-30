"""Independent check — InvestAI Long Short v3 (BJDRgy7z): daily bars, slippage 0. Raw long = EMA9 crossing over EMA21 with 30 < RSI14 < 70 and MACD(12,26,9) line > signal; raw short mirrors (cross under, MACD line < signal). The signal is the PREVIOUS bar's raw signal (confirmation); it enters at the next open,
reversing an open opposite trade, and sets stop = close -/+ 1 ATR14 and target = close +/- 4 ATR14 (of the confirmation bar) for that direction, also when already in the trade."""
import numpy as np

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "BJDRgy7z"


def check():
    df = bars(9000, seed=71)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    f, s = np_ema(c, 9), np_ema(c, 21)
    rsi, atr = np_rsi(c, 14), np_atr(h, l, c, 14)
    macd = np_ema(c, 12) - np_ema(c, 26)
    sig = np_ema(macd, 9)
    with np.errstate(invalid="ignore"):
        lr = np_cross_over(f, s) & (rsi > 30) & (rsi < 70) & (macd > sig)
        sr = np_cross_under(f, s) & (rsi < 70) & (rsi > 30) & (macd < sig)
    ls, ss = np.r_[False, lr[:-1]], np.r_[False, sr[:-1]]
    lvl = {}

    def orders(i, pos):
        out = []
        if ls[i]:
            out.append(("entry", 1))
            lvl[1] = (c[i] - atr[i], c[i] + atr[i] * 4)
        if ss[i]:
            out.append(("entry", -1))
            lvl[-1] = (c[i] + atr[i], c[i] - atr[i] * 4)
        return out

    def stop(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][0]

    def target(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
