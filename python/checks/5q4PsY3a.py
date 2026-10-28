"""Independent check — XAUUSD Scalping V2 AGRESIV (5q4PsY3a): 5-min bars. EMA 5/13 cross with RSI(7) beyond 55/45 and ATR>0.5 reverses; bracket
1.2 ATR target / 0.8 ATR stop from the signal close, placed with the entry (works from the fill bar). trail_points without trail_offset never
trails in Pine, so only the fixed levels act."""
import numpy as np

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "5q4PsY3a"


def check():
    df = bars(20000, seed=131, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    f, s, rsi, atr = np_ema(c, 5), np_ema(c, 13), np_rsi(c, 7), np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        lg = np_cross_over(f, s) & (rsi > 55) & (atr > 0.5)
        sg = np_cross_under(f, s) & (rsi < 45) & (atr > 0.5)
    cur = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}
    hist = []

    def orders(i, pos):
        out = []
        if lg[i]:
            out.append(("entry", 1)); cur[1] = (c[i] - atr[i] * 0.8, c[i] + atr[i] * 1.2)
        if sg[i]:
            out.append(("entry", -1)); cur[-1] = (c[i] + atr[i] * 0.8, c[i] - atr[i] * 1.2)
        hist.append(dict(cur))
        return out

    ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: hist[i - 1][pos][0] if i > 0 else None,
                   target=lambda i, pos, ep, eb: hist[i - 1][pos][1] if i > 0 else None)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
