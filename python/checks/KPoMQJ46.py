"""Independent check — My strategy 9 (KPoMQJ46): daily bars. SMA14 crossing over SMA28 goes long, crossing under goes short (reversing, 1 contract, no brackets)."""
from indep import bars, compare, np_cross_over, np_cross_under, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "KPoMQJ46"


def check():
    df = bars(4000, seed=201)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    a, b = np_sma(c, 14), np_sma(c, 28)
    up, dn = np_cross_over(a, b), np_cross_under(a, b)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if up[i] else []) + ([("entry", -1)] if dn[i] else []))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
