"""Independent check — XAUUSD Auto Strategy (Ae37AI2n): 5-min bars. Close crossing the EMA20 in the direction of the EMA20/50 trend reverses; the
bracket (2 ATR stop, 4 ATR target from the signal close) is placed with the entry and works from the fill bar. Quantity (risk based) does not
change prices and is not compared."""
import numpy as np

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "Ae37AI2n"


def check():
    df = bars(20000, seed=117, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    f, s, atr = np_ema(c, 20), np_ema(c, 50), np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        buy = (f > s) & np_cross_over(c, f)
        sell = (f < s) & np_cross_under(c, f)
    cur = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}
    hist = []

    def orders(i, pos):
        out = []
        if buy[i]:
            out.append(("entry", 1)); cur[1] = (c[i] - atr[i] * 2.0, c[i] + atr[i] * 4.0)
        if sell[i]:
            out.append(("entry", -1)); cur[-1] = (c[i] + atr[i] * 2.0, c[i] - atr[i] * 4.0)
        hist.append(dict(cur))
        return out

    ref = simulate(o, h, l, c, orders,
                   stop=lambda i, pos, ep, eb: hist[i - 1][pos][0] if i > 0 else None,
                   target=lambda i, pos, ep, eb: hist[i - 1][pos][1] if i > 0 else None)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
