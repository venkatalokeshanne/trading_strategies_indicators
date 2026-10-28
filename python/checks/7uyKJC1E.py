"""Independent check — NIFTY Swing Target Engine (7uyKJC1E): 5-min New York bars. A bar in 09:20-15:00 Mon-Fri whose body is >= 70 % of its range, green -> long, red -> short (reversing; entry when pos <= 0 / >= 0). Each signal
stores target = close -/+ 3 ATR14 and stop = previous bar's low / high; while a position is open at the close the stop is math.max / math.min'ed with the 3-bar lowest low / highest high (na on either side stays na; the
windows only hold values fed on bars where that branch ran) and a bracket (limit target, stop trail) is issued for it, working from the next bar; flat at the close resets both to na (so a trade from flat has no bracket)."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "7uyKJC1E"


def check():
    df = bars(60000, seed=226, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    win = (m >= 560) & (m < 900) & (ny.dt.dayofweek.to_numpy() <= 4)
    atr = np_atr(h, l, c, 14)
    rng = h - l
    with np.errstate(invalid="ignore", divide="ignore"):
        pct = np.where(rng > 0, np.abs(c - o) / rng * 100, 0.0)
    fl, fs = win & (c > o) & (pct >= 70), win & (c < o) & (pct >= 70)
    tgt, tsl = np.nan, np.nan
    fed_lo, fed_hi = [], []
    store, poscl = [None] * n, np.zeros(n)

    def nmax(a, b):
        return np.nan if (np.isnan(a) or np.isnan(b)) else max(a, b)

    def nmin(a, b):
        return np.nan if (np.isnan(a) or np.isnan(b)) else min(a, b)

    def orders(i, pos):
        nonlocal tgt, tsl
        poscl[i] = pos
        out = []
        if fl[i] and pos <= 0:
            out.append(("entry", 1)); tgt = c[i] + atr[i] * 3.0; tsl = l[i - 1] if i else np.nan
        if fs[i] and pos >= 0:
            out.append(("entry", -1)); tgt = c[i] - atr[i] * 3.0; tsl = h[i - 1] if i else np.nan
        if pos > 0:
            fed_lo.append(l[i]); tsl = nmax(tsl, min(fed_lo[-3:]) if len(fed_lo) >= 3 else np.nan)
        if pos < 0:
            fed_hi.append(h[i]); tsl = nmin(tsl, max(fed_hi[-3:]) if len(fed_hi) >= 3 else np.nan)
        store[i] = (tsl, tgt) if pos != 0 else None
        if pos == 0:
            tgt = tsl = np.nan
        return out

    def level(k):
        def fn(i, pos, ep, eb):
            if i == 0 or store[i - 1] is None or poscl[i - 1] != pos:
                return None
            v = store[i - 1][k]
            return None if np.isnan(v) else v
        return fn

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
