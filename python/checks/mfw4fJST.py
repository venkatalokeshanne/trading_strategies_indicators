"""Independent check — VIX MACD Long (mfw4fJST): a synthetic 'VIX' supplied through the data provider."""
from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate


def check():
    df = bars(3000, seed=31)
    vix = bars(3000, seed=99)                    # stands in for CBOE:VIX on the same bar times
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = vix["close"].to_numpy()
    macd = np_ema(v, 12) - np_ema(v, 26)
    sig = np_ema(macd, 9)
    lc, xc = np_cross_under(macd, sig), np_cross_over(macd, sig)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if lc[i] else []) + ([("close", 1)] if xc[i] else []))
    return compare(run_conversion("mfw4fJST", df, data_provider=lambda sym, tf: vix), ref)
