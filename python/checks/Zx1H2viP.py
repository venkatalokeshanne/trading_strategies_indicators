"""Independent check — Evasive SuperTrend (Zx1H2viP): 5-min bars. Supertrend-like line from hl2 +/- 3 ATR(10) with a noise rule (close within 1 ATR of the line makes
it drift away by 0.5 ATR instead of following the band); a trend flip opens the position in the new direction (reversing, no exits). math.max/min return na if either
operand is na, nz() falls back to the current band while the line has no history. Written as a plain loop."""
import numpy as np

from indep import bars, compare, np_atr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "Zx1H2viP"


def nmax(a, b):
    return np.nan if (np.isnan(a) or np.isnan(b)) else max(a, b)


def nmin(a, b):
    return np.nan if (np.isnan(a) or np.isnan(b)) else min(a, b)


def check():
    df = bars(20000, seed=157, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr = np_atr(h, l, c, 10)
    src = (h + l) / 2
    trend, line = 1, np.nan
    tr = np.zeros(n, int)
    for i in range(n):
        up, lo = src[i] + 3.0 * atr[i], src[i] - 3.0 * atr[i]
        prev = line if not np.isnan(line) else (lo if trend == 1 else up)       # nz(st_line[1], default)
        noisy = abs(c[i] - prev) < atr[i] * 1.0
        if trend == 1:
            line = prev - atr[i] * 0.5 if noisy else nmax(lo, prev)
            if c[i] < line:
                trend, line = -1, up
        else:
            line = prev + atr[i] * 0.5 if noisy else nmin(up, prev)
            if c[i] > line:
                trend, line = 1, lo
        tr[i] = trend
    chg = np.r_[0, np.diff(tr)]
    chg[0] = 0                                     # ta.change on the first bar is na -> false

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if chg[i] > 0 else []) + ([("entry", -1)] if chg[i] < 0 else []))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
