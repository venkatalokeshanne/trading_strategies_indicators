"""Independent check — MACD + EMA18 Signal (gFzmy44j, same script as ZJZb6mII): daily bars. A MACD(12,26,9) cross with the close on the matching side of EMA18 opens a position when flat; a long closes when the close < SMA(low,10)
or MACD crosses under, a short when the close > SMA(high,10) or MACD crosses over. The entry crosses run every bar; the cross inside the exit test is a separate call site that (v6 short-circuit) only runs while that side is open
and the SMA test did not already fire, and its previous values are those of its last run (LESSONS P4/P5)."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, np_sma, run_conversion, simulate
from pinelib import SymbolInfo


def build(tv_id, seed):
    df = bars(6000, seed=seed)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    m = np_ema(c, 12) - np_ema(c, 26)
    sig = np_ema(m, 9)
    up, dn = np_cross_over(m, sig), np_cross_under(m, sig)
    e18, sh, sl = np_ema(c, 18), np_sma(h, 10), np_sma(l, 10)
    with np.errstate(invalid="ignore"):
        buy, sell = up & (c > e18), dn & (c < e18)
        below_sl, above_sh = c < sl, c > sh
    st = dict(lm=np.nan, ls=np.nan, sm=np.nan, ss=np.nan)             # last values seen by the in-block crossunder / crossover

    def orders(i, pos):
        out = []
        if pos == 0:
            if buy[i]:
                out.append(("entry", 1))
            if sell[i]:
                out.append(("entry", -1))
        if pos > 0 and not below_sl[i]:
            xu = bool(m[i] < sig[i] and st["lm"] >= st["ls"])
            st["lm"], st["ls"] = m[i], sig[i]
            if xu:
                out.append(("close", 1))
        elif pos > 0:
            out.append(("close", 1))
        if pos < 0 and not above_sh[i]:
            xo = bool(m[i] > sig[i] and st["sm"] <= st["ss"])
            st["sm"], st["ss"] = m[i], sig[i]
            if xo:
                out.append(("close", -1))
        elif pos < 0:
            out.append(("close", -1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(tv_id, df, symbol=sym, tf="D"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"


TV_ID = "gFzmy44j"


def check():
    return build(TV_ID, 205)
