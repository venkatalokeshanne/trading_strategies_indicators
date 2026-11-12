"""Independent check — Stable Main Force v6 (7rQKeCN2): 5-min bars. Breakout above the 20-bar high of the PRIOR bars with
volume 1.2x SMA20, EMA21>EMA50 and OBV(EMA5) above its SMA20; stop = min(10-bar low, EMA50) - 0.5 ATR, target 2R. The exit
is re-issued every bar, so bar i works with bar i-1's levels (also on the fill bar)."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "7rQKeCN2"


def roll(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        if not np.isnan(w).any():
            out[i] = fn(w)
    return out


def check():
    df = bars(20000, seed=85, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    e21, e50, vma, atr = np_ema(c, 21), np_ema(c, 50), np_sma(v, 20), np_atr(h, l, c, 14)
    pc = np.r_[np.nan, c[:-1]]
    with np.errstate(invalid="ignore"):
        raw = np.cumsum(np.where(c > pc, v, np.where(c < pc, -v, 0.0)))
    obv = np_ema(raw, 5)
    obv_ma = np_sma(obv, 20)
    hi20 = roll(np.r_[np.nan, h[:-1]], 20, np.max)
    low10 = roll(l, 10, np.min)
    stop = np.fmin(low10, e50) - atr * 0.5
    risk = c - stop
    risk = np.where(risk > 0, risk, np.nan)
    with np.errstate(invalid="ignore"):
        sig = (c > hi20) & (v > vma * 1.2) & (e21 > e50) & (obv > obv_ma) & ~np.isnan(risk)
    tp = c + risk * 2

    ref = simulate(o, h, l, c, lambda i, pos: [("entry", 1)] if sig[i] else [],
                   stop=lambda i, pos, ep, eb: stop[i - 1] if i > 0 else None,
                   target=lambda i, pos, ep, eb: tp[i - 1] if i > 0 else None)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
