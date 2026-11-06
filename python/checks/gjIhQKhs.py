"""Independent check — BTC Directional Trend + Trailing SL (gjIhQKhs): 5-min bars. Close crossing the EMA20 in the direction of the
EMA200 trend; the exit is a trailing stop re-issued every bar with activation = ATR*2 ticks and offset = ATR ticks (mintick 0.01).
It is pending before the fill, so it already works on the fill bar.
v6 + 100 % of equity would refuse entries when the fill open is above the signal close (LESSONS P12); margin is
switched off on the pinelib side so this check covers the signal and trailing logic only. Uses indep.exit_hit's trailing model."""
import numpy as np

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "gjIhQKhs"


def check():
    df = bars(20000, seed=88, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    e200, e20, atr = np_ema(c, 200), np_ema(c, 20), np_atr(h, l, c, 14)
    n = len(c)
    lg, sh = np.zeros(n, bool), np.zeros(n, bool)
    # Pine v6 short-circuits `uptrend and ta.crossover(...)`: the cross only RUNS on bars where the trend filter is true,
    # so its "previous bar" is the last bar it ran on (LESSONS P4/P5), not bar i-1.
    up_state = dn_state = None
    for i in range(n):
        if c[i] > e200[i]:
            lg[i] = up_state is not None and c[i] > e20[i] and up_state[0] <= up_state[1]
            up_state = (c[i], e20[i])
        if c[i] < e200[i]:
            sh[i] = dn_state is not None and c[i] < e20[i] and dn_state[0] >= dn_state[1]
            dn_state = (c[i], e20[i])

    def trail(i, pos, ep, eb):
        return None if (i == 0 or np.isnan(atr[i - 1])) else (atr[i - 1] * 2.0, atr[i - 1])

    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if lg[i] else []) + ([("entry", -1)] if sh[i] else []),
                   trail=trail, tick=0.01)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
