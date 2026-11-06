"""Independent check — EMA CrossX (8al2ILgk): 5-min bars, long only. An EMA 9/19 bullish cross enters 2 bars later (enterLong[i] = cross[i-2]). While long, the exit
is re-issued every bar (works from the bar after the fill): trailing option = stop at entry - 2.5 + a trailing stop active from the entry price (trail_points 0)
following by 1.0 point (100 ticks); fixed option = stop entry - 2.5 and limit entry + 4. Both options are run (the second through the input) and the
trade counts added."""
import numpy as np

from indep import bars, compare, np_cross_over, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "8al2ILgk"


def one(seed, trailing):
    df = bars(20000, seed=seed, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    cross = np_cross_over(np_ema(c, 9), np_ema(c, 19))
    enter = np.r_[[False] * 2, cross[:-2]]
    if trailing:
        ref = simulate(o, h, l, c, lambda i, pos: [("entry", 1)] if enter[i] else [],
                       stop=lambda i, pos, ep, eb: ep - 2.5 if i > eb else None,
                       trail=lambda i, pos, ep, eb: (0.0, 100.0) if i > eb else None, tick=0.01)
    else:
        ref = simulate(o, h, l, c, lambda i, pos: [("entry", 1)] if enter[i] else [],
                       stop=lambda i, pos, ep, eb: ep - 2.5 if i > eb else None,
                       target=lambda i, pos, ep, eb: ep + 4.0 if i > eb else None)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    params = {} if trailing else {"Enable Trailing Stop (Overrides Fixed TP)?": False}
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params), ref)
    return ok, detail, len(ref)


def check():
    res = [one(160, True), one(161, False)]
    bad = [r[1] for r in res if not r[0]]
    total = sum(r[2] for r in res)
    return (not bad) and total > 10, (bad[0] if bad else f"{res[0][2]} trailing + {res[1][2]} fixed trades identical") + f" (need >10 trades, got {total})"
