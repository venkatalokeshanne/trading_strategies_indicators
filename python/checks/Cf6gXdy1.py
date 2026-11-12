"""Independent check — Moja Strategia Harami BB (Cf6gXdy1): 5-min bars. After a candle that touched the Bollinger band (20, 2) of ITS OWN bar, a candle whose body is inside the previous
body (harami) reverses the position: bullish after a down candle that touched the lower band, bearish after an up candle that touched the upper band. Exits are unconditional and
pending before the fill: profit 40 ticks / loss 20 ticks (mintick 0.01), so they already work on the fill bar. Cash sizing does not change prices."""
import numpy as np

from indep import bars, compare, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "Cf6gXdy1"


def check():
    df = bars(20000, seed=177, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    basis = np_sma(c, 20)
    sd = np.full(n, np.nan)
    for i in range(19, n):
        sd[i] = np.std(c[i - 19:i + 1])
    up, lo = basis + 2.0 * sd, basis - 2.0 * sd
    p = lambda x: np.r_[np.nan, x[:-1]]
    o1, c1, h1, l1, up1, lo1 = p(o), p(c), p(h), p(l), p(up), p(lo)
    with np.errstate(invalid="ignore"):
        inside = (np.maximum(o, c) <= np.fmax(o1, c1)) & (np.minimum(o, c) >= np.fmin(o1, c1))
        bull = (l1 <= lo1) & (c1 < o1) & inside
        bear = (h1 >= up1) & (c1 > o1) & inside
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if bull[i] else []) + ([("entry", -1)] if bear[i] else []),
                   stop=lambda i, pos, ep, eb: ep - pos * 20 * 0.01, target=lambda i, pos, ep, eb: ep + pos * 40 * 0.01)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
