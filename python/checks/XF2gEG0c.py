"""Independent check — WMA + RSI Filtreli Scalp (XF2gEG0c): WMA 9/21 cross with trend/RSI filter,
stop-and-reverse at the next open."""
from indep import bars, compare, np_cross_over, np_cross_under, np_rsi, np_wma, run_conversion, simulate

TV_ID = "XF2gEG0c"


def check():
    df = bars(3000, seed=67)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    f, s, rsi = np_wma(c, 9), np_wma(c, 21), np_rsi(c, 14)
    lc = np_cross_over(f, s) & (c > f) & (c > s) & (rsi > 50)
    sc = np_cross_under(f, s) & (c < f) & (c < s) & (rsi < 50)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if lc[i] else []) + ([("entry", -1)] if sc[i] else []))
    return compare(run_conversion(TV_ID, df), ref)
