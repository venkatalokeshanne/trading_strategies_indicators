"""Independent check — SuperTrend BB (anNnwsQo): hourly bars. np_supertrend(3, 10) flipping to up (down) with close above (below) SMA50 enters long (short) when flat; entry + exit are issued on the signal bar (stop = close -/+
1.5 ATR14, limit = 1.5 R), so the bracket works from the fill bar. Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_atr, np_sma, np_supertrend, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "anNnwsQo"


def check():
    df = bars(30000, seed=264, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    _, d = np_supertrend(h, l, c, 3.0, 10)
    d1 = np.r_[np.nan, d[:-1]]
    mid, atr = np_sma(c, 50), np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        bs, ss = (d == -1) & (d1 == 1) & (c > mid), (d == 1) & (d1 == -1) & (c < mid)
    lvl = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}

    def orders(i, pos):
        out = []
        if bs[i] and pos == 0:
            sl = c[i] - atr[i] * 1.5
            out.append(("entry", 1)); lvl[1] = (sl, c[i] + (c[i] - sl) * 1.5)
        if ss[i] and pos == 0:
            sl = c[i] + atr[i] * 1.5
            out.append(("entry", -1)); lvl[-1] = (sl, c[i] - (sl - c[i]) * 1.5)
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: lvl[pos][0], target=lambda i, pos, ep, eb: lvl[pos][1])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
