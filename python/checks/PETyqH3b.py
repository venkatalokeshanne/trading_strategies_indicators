"""Independent check — EMA Pullback (PETyqH3b): daily bars, EMA 30 / 80 here (passed to both sides). EMA fast > slow, close > fast EMA and (previous low <= previous fast EMA or previous close < previous fast EMA), volume > SMA20(volume), RSI14 > 40, flat -> long; mirror with RSI < 60.
Stop = lowest low of 5 bars (current included) - 0.5 ATR14 (short: highest high + 0.5 ATR), target = close +/- 2.5 ATR14, fixed on the signal bar."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "PETyqH3b"
F, SL_ = 30, 80


def check():
    df = bars(9000, seed=96)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    ef, es = np_ema(c, F), np_ema(c, SL_)
    rsi, atr = np_rsi(c, 14), np_atr(h, l, c, 14)
    l1, h1, c1, ef1 = (np.r_[np.nan, x[:-1]] for x in (l, h, c, ef))
    sw_l = pd.Series(l).rolling(5).min().to_numpy()
    sw_h = pd.Series(h).rolling(5).max().to_numpy()
    with np.errstate(invalid="ignore"):
        vol = v > np_sma(v, 20)
        lg = (ef > es) & (c > ef) & ((l1 <= ef1) | (c1 < ef1)) & vol & (rsi > 40)
        sh = (ef < es) & (c < ef) & ((h1 >= ef1) | (c1 > ef1)) & vol & (rsi < 60)
    lvl = {}

    def orders(i, pos):
        out = []
        if pos == 0 and lg[i]:
            out.append(("entry", 1))
            lvl[1] = (sw_l[i] - atr[i] * 0.5, c[i] + atr[i] * 2.5)
        if pos == 0 and sh[i]:
            out.append(("entry", -1))
            lvl[-1] = (sw_h[i] + atr[i] * 0.5, c[i] - atr[i] * 2.5)
        return out

    def stop(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][0]

    def target(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Fast EMA (Pullback Level)": F, "Slow EMA (Trend Filter)": SL_},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
