"""Independent check — MA Crossover + RSI (UCGXkLvt): 5-min bars, long only. EMA9 crossing over EMA21 with RSI<70 buys; the opposite cross
with RSI>30 closes (only if the long exists); while long a 2 % stop / 4 % target on the average price, from the bar after the fill."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "UCGXkLvt"


def check():
    df = bars(20000, seed=104, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    f, s, rsi = np_ema(c, 9), np_ema(c, 21), np_rsi(c, 14)
    with np.errstate(invalid="ignore"):
        buy = np_cross_over(f, s) & (rsi < 70)
        sell = np_cross_under(f, s) & (rsi > 30)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if buy[i] else []) + ([("close", 1)] if sell[i] and pos > 0 else []),
                   stop=lambda i, pos, ep, eb: ep * 0.98 if i > eb else None,
                   target=lambda i, pos, ep, eb: ep * 1.04 if i > eb else None)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
