"""Independent check — Sniper Scalping Bot (isp5rkkS), Pine v6: the crossover/crossunder only
run on bars where the EMA200 filter holds (lazy `and`), so their previous value is the one
from the last bar they ran. Brackets: 30 / 15 ticks from the entry price (mintick 0.01)."""
import numpy as np

from indep import bars, compare, np_ema, np_rsi, run_conversion, simulate

TV_ID = "isp5rkkS"
TICK = 0.01


def lazy_cross(c, e, gate, over):
    out, prev = np.zeros(len(c), bool), (np.nan, np.nan)
    for i in range(len(c)):
        if gate[i]:
            a, b = c[i], e[i]
            out[i] = (a > b and prev[0] <= prev[1]) if over else (a < b and prev[0] >= prev[1])
            prev = (a, b)
    return out


def check():
    df = bars(3000, seed=41)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    e20, e200, rsi = np_ema(c, 20), np_ema(c, 200), np_rsi(c, 14)
    bull, bear = c > e200, c < e200
    lc = lazy_cross(c, e20, bull, True) & (rsi > 55)
    sc = lazy_cross(c, e20, bear, False) & (rsi < 45)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if lc[i] else []) + ([("entry", -1)] if sc[i] else []),
                   stop=lambda i, pos, ep, eb: ep - pos * 15 * TICK,
                   target=lambda i, pos, ep, eb: ep + pos * 30 * TICK)
    return compare(run_conversion(TV_ID, df), ref)
