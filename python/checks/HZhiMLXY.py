"""Independent check — HS SP500 1.6x Long (HZhiMLXY): in-window long, fills at the close, 2-tick slippage."""
from indep import bars, compare, run_conversion, simulate


def check():
    df = bars(4300, seed=30)                     # runs past the window end (2026-05-26)
    o, h, l, c, t = (df[k].to_numpy() for k in ("open", "high", "low", "close", "time"))
    start, end = 1521158400000, 1779753600000
    inw = (t >= start) & (t <= end)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if inw[i] and pos <= 0 else [])
                   + ([("close", 1)] if (not inw[i]) and pos > 0 else []), on_close=True, slip=2 * 0.01)
    return compare(run_conversion("HZhiMLXY", df), ref)
