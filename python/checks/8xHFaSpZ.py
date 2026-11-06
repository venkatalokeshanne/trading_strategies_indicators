"""Independent check — Fair Value Gap Strategy (8xHFaSpZ): 5-min bars; high two bars ago below this low = long, low two bars ago above
this high = short; opposite signals reverse; no exits; 1 contract."""
import numpy as np

from indep import bars, compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "8xHFaSpZ"


def check():
    df = bars(5000, seed=91, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    h2, l2 = np.r_[[np.nan] * 2, h[:-2]], np.r_[[np.nan] * 2, l[:-2]]
    with np.errstate(invalid="ignore"):
        bull, bear = h2 < l, l2 > h
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if bull[i] else []) + ([("entry", -1)] if bear[i] else []))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
