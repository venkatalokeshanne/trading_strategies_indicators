"""Independent check — EMA + MACD + RSI Confluence (Ospkem6i): long/short confluence entries;
strategy.exit runs every bar, so the bracket on bar i is built from close[i-1]."""
from indep import bars, compare, np_ema, np_rsi, run_conversion, simulate

TV_ID = "Ospkem6i"


def check():
    df = bars(3000, seed=31)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    f, s, rsi = np_ema(c, 9), np_ema(c, 20), np_rsi(c, 14)
    macd = np_ema(c, 12) - np_ema(c, 26)
    hist = macd - np_ema(macd, 9)
    lc = (c > f) & (c > s) & (rsi > 50) & (hist > 0)
    sc = (c < f) & (c < s) & (rsi < 50) & (hist < 0)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if lc[i] else []) + ([("entry", -1)] if sc[i] else []),
                   stop=lambda i, pos, ep, eb: c[i - 1] * (0.982 if pos > 0 else 1.018),
                   target=lambda i, pos, ep, eb: c[i - 1] * (1.06 if pos > 0 else 0.94))
    return compare(run_conversion(TV_ID, df), ref)
