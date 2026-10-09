"""Independent check — TEST Verificacion Ordenes (NWIwEuKt): EMA 20/50 cross reversal filled at
the signal close (process_orders_on_close). Run at 100 % of equity: the original 10 000 %
wipes the account on the first losing trade, after which no order can be sized."""
from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate

TV_ID = "NWIwEuKt"


def check():
    df = bars(3000, seed=83)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    f, s = np_ema(c, 20), np_ema(c, 50)
    up, dn = np_cross_over(f, s), np_cross_under(f, s)
    ref = simulate(o, h, l, c, lambda i, pos: ([("close", -1), ("entry", 1)] if up[i] else [])
                   + ([("close", 1), ("entry", -1)] if dn[i] else []), on_close=True)
    return compare(run_conversion(TV_ID, df, strategy_overrides=dict(default_qty_value=100)), ref)
