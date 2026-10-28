"""Independent check — Order Block Strategy (WTvOUjFA): daily bars, ATR multiplier 1.5 here (passed to both sides). A confirmed pivot low / high (10 bars each side, strict) stores that pivot bar's [low, high] as the bullish / bearish block. A bullish
candle closing inside the bullish block enters long when flat, a bearish candle inside the bearish block enters short; bracket = close -/+ ATR14*1.5 and close +/- 1.5x that, fixed on the signal bar."""
import numpy as np

from indep import bars, compare, np_atr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "WTvOUjFA"
K, MULT, RR = 10, 1.5, 1.5


def check():
    df = bars(8000, seed=47)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr = np_atr(h, l, c, 14)
    bh = bl = sh = sl = np.nan
    lvl = {}
    st = dict(bh=np.nan, bl=np.nan, sh=np.nan, sl=np.nan)

    def orders(i, pos):
        out = []
        if i >= 2 * K:
            m = i - K
            wl = l[m - K:m + K + 1]
            if l[m] == wl.min() and (wl == l[m]).sum() == 1:
                st["bh"], st["bl"] = h[m], l[m]
            wh = h[m - K:m + K + 1]
            if h[m] == wh.max() and (wh == h[m]).sum() == 1:
                st["sh"], st["sl"] = h[m], l[m]
        d = atr[i] * MULT
        with np.errstate(invalid="ignore"):
            lc = not np.isnan(st["bh"]) and c[i] <= st["bh"] and c[i] >= st["bl"] and c[i] > o[i]
            sc = not np.isnan(st["sh"]) and c[i] >= st["sl"] and c[i] <= st["sh"] and c[i] < o[i]
        if lc and pos == 0:
            out.append(("entry", 1))
            lvl[1] = (c[i] - d, c[i] + d * RR)
        if sc and pos == 0:
            out.append(("entry", -1))
            lvl[-1] = (c[i] + d, c[i] - d * RR)
        return out

    def stop(i, pos, ep, eb):
        v = lvl[1 if pos > 0 else -1][0]
        return None if np.isnan(v) else v

    def target(i, pos, ep, eb):
        v = lvl[1 if pos > 0 else -1][1]
        return None if np.isnan(v) else v

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"ATR Multiplier (SL)": MULT},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
