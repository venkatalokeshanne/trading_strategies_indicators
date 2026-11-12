"""Independent check — Stochastic Bot with SL/TP (EVvWJ4Us): 5-min bars, long only. %K = SMA(3) of the 14-bar stochastic, %D = SMA(3) of %K; a %K cross
up through %D below 20 buys; while long the exit (-2.5 % stop / +6 % target on the entry price) is re-issued each bar (works from the bar after the
fill) and a %K cross down through %D above 60 closes the long."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_sma, np_stoch, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "EVvWJ4Us"


def check():
    df = bars(20000, seed=123, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    k = np_sma(np_stoch(c, h, l, 14), 3)
    d = np_sma(k, 3)
    with np.errstate(invalid="ignore"):
        buy = np_cross_over(k, d) & (k < 20)
        sell = np_cross_under(k, d) & (k > 60)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if buy[i] else []) + ([("close", 1)] if sell[i] and pos > 0 else []),
                   stop=lambda i, pos, ep, eb: ep * (1 - 0.025) if i > eb else None,
                   target=lambda i, pos, ep, eb: ep * (1 + 0.06) if i > eb else None)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
