"""Independent check — BTC 4H Trend v4 (zuEOEYPK): daily bars, shorts enabled (passed to both sides), slippage 0. Long: (EMA21 crosses over EMA55, or EMA21 > EMA55 with close > EMA21 and close[1] < EMA21), close > EMA200 and EMA200 > EMA200[3], RSI14 < 70,
flat; short mirrors with RSI > 30. The bracket is fixed at the signal bar: stop = close -/+ 1.5 ATR14, target = close +/- 3 ATR14, trailing stop activating after ATR*1.5 TICKS (0.01) with the same offset in ticks."""
import numpy as np

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "zuEOEYPK"


def check():
    df = bars(8000, seed=26)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    f, s, t = np_ema(c, 21), np_ema(c, 55), np_ema(c, 200)
    rsi, atr = np_rsi(c, 14), np_atr(h, l, c, 14)
    t3 = np.r_[[np.nan] * 3, t[:-3]]
    c1, = (np.r_[np.nan, c[:-1]],)
    with np.errstate(invalid="ignore"):
        lg = (np_cross_over(f, s) | ((f > s) & (c > f) & (c1 < f))) & (c > t) & (t > t3) & (rsi < 70)
        sh = (np_cross_under(f, s) | ((f < s) & (c < f) & (c1 > f))) & (c < t) & (t < t3) & (rsi > 30)
    lvl = {}

    def orders(i, pos):
        out = []
        if pos == 0:
            if lg[i]:
                out.append(("entry", 1))
                lvl[1] = (c[i] - atr[i] * 1.5, c[i] + atr[i] * 3, atr[i] * 1.5)
            if sh[i]:
                out.append(("entry", -1))
                lvl[-1] = (c[i] + atr[i] * 1.5, c[i] - atr[i] * 3, atr[i] * 1.5)
        return out

    def stop(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][0]

    def target(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][1]

    def trail(i, pos, ep, eb):
        tr = lvl[1 if pos > 0 else -1][2]
        return (tr, tr)

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target, trail=trail, tick=0.01)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"ショート有効（推奨: OFF）": True},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
