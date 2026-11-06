"""Independent check — NAS100 EMA Scalper (s8NYoQF9): EMA10/20 cross in the direction of the EMA50/200 trend with the 5/10/20
stack aligned and a candle of that colour; no exits, opposite signals reverse. Hourly bars (long EMA warm-up)."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "s8NYoQF9"


def check():
    df = bars(20000, seed=84, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    e5, e10, e20, e50, e200 = (np_ema(c, n) for n in (5, 10, 20, 50, 200))
    with np.errstate(invalid="ignore"):
        lg = (e50 > e200) & np_cross_over(e10, e20) & (e5 > e10) & (e10 > e20) & (c > o)
        sh = (e50 < e200) & np_cross_under(e10, e20) & (e5 < e10) & (e10 < e20) & (c < o)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if lg[i] else []) + ([("entry", -1)] if sh[i] else []))
    sym = SymbolInfo.make("NASDAQ:QQQ", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
