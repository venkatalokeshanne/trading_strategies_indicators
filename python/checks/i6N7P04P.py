"""Independent check — 5m SOL Scalper HA + Lorentzian (i6N7P04P): 5-min bars. EMA(8) of each OHLC price makes a smoothed Heikin-Ashi candle (haOpen
starts at (sOpen+sClose)/2 while its history is na, then (prev haOpen + prev haClose)/2); a haClose cross of haOpen with the sign of the least-squares
end value of the 14-bar price change (numpy polyfit) reverses the position with a +1.5 % / -0.8 % bracket placed with the entry (works from the fill bar)."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "i6N7P04P"


def check():
    df = bars(12000, seed=154, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    so, sh, sl, sc = (np_ema(x, 8) for x in (o, h, l, c))
    hac = (so + sh + sl + sc) / 4
    hao = np.full(n, np.nan)
    for i in range(n):
        prev = hao[i - 1] if i else np.nan
        hao[i] = (so[i] + sc[i]) / 2 if np.isnan(prev) else (prev + hac[i - 1]) / 2
    c14 = np.r_[[np.nan] * 14, c[:-14]]
    x = c - c14
    vel = np.full(n, np.nan)
    xs = np.arange(14, dtype=float)
    for i in range(13, n):
        w = x[i - 13:i + 1]
        if not np.isnan(w).any():
            slope, icpt = np.polyfit(xs, w, 1)
            vel[i] = icpt + slope * 13
    with np.errstate(invalid="ignore"):
        lg = np_cross_over(hac, hao) & (vel > 0)
        sg = np_cross_under(hac, hao) & (vel < 0)
    cur = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}
    hist = []

    def orders(i, pos):
        out = []
        if lg[i]:
            out.append(("entry", 1)); cur[1] = (c[i] * (1 - 0.008), c[i] * (1 + 0.015))
        if sg[i]:
            out.append(("entry", -1)); cur[-1] = (c[i] * (1 + 0.008), c[i] * (1 - 0.015))
        hist.append(dict(cur))
        return out

    ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: hist[i - 1][pos][0] if i > 0 else None,
                   target=lambda i, pos, ep, eb: hist[i - 1][pos][1] if i > 0 else None)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
