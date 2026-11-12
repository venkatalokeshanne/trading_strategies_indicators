"""Independent check — Box Breakout (pH26SUal): 5-min bars. Box = highest high / lowest low of the PRIOR bars over 20 (series argument high[1]/low[1], so the
first window holds 19 real values: na values are skipped); a close outside the box with volume above its SMA20 enters with a 1.5 ATR stop and a 2R target
from the signal close, placed with the entry (works from the fill bar). Opposite signals reverse."""
import numpy as np

from indep import bars, compare, np_atr, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "pH26SUal"


def roll(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        w = w[~np.isnan(w)]
        if len(w):
            out[i] = fn(w)
    return out


def check():
    df = bars(20000, seed=142, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    h1, l1 = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    bh, bl = roll(h1, 20, np.max), roll(l1, 20, np.min)
    atr = np_atr(h, l, c, 14)
    vc = v > np_sma(v, 20)
    with np.errstate(invalid="ignore"):
        up, dn = (c > bh) & vc, (c < bl) & vc
    cur = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}
    hist = []

    def orders(i, pos):
        out = []
        if up[i]:
            s = c[i] - atr[i] * 1.5
            out.append(("entry", 1)); cur[1] = (s, c[i] + (c[i] - s) * 2.0)
        if dn[i]:
            s = c[i] + atr[i] * 1.5
            out.append(("entry", -1)); cur[-1] = (s, c[i] - (s - c[i]) * 2.0)
        hist.append(dict(cur))
        return out

    ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: hist[i - 1][pos][0] if i > 0 else None,
                   target=lambda i, pos, ep, eb: hist[i - 1][pos][1] if i > 0 else None)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
