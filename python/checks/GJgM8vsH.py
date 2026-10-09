"""Independent check — Trend Pullback EMA50/EMA200 + WaveTrend (GJgM8vsH): fills at the signal
close (process_orders_on_close) with 1 tick (0.01) of slippage."""
from indep import bars, compare, np_cross_over, np_cross_under, np_ema, np_sma, run_conversion, simulate

TV_ID = "GJgM8vsH"


def check():
    df = bars(3000, seed=47)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    e50, e200 = np_ema(c, 50), np_ema(c, 200)
    esa = np_ema(c, 9)
    d = np_ema(abs(c - esa), 9)
    wt1 = np_ema((c - esa) / (0.015 * d), 12)
    wt2 = np_sma(wt1, 3)
    lc = (c > e200) & (c < e50) & np_cross_over(wt1, wt2)
    sc = (c < e200) & (c > e50) & np_cross_under(wt1, wt2)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if lc[i] else []) + ([("entry", -1)] if sc[i] else []),
                   on_close=True, slip=0.01)
    return compare(run_conversion(TV_ID, df), ref)
