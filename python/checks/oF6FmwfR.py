"""Independent check — Pro SMA Trend (oF6FmwfR): daily bars. Close crossing over SMA44 enters long, under enters short (reversing); in "Long Only" the cross under only closes the long, in "Short Only" the cross over
only closes the short. Run for all three Trade Direction settings. Quantity is leverage-sized (irrelevant to prices); margin off on the pinelib side."""
from indep import bars, compare, np_cross_over, np_cross_under, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "oF6FmwfR"


def check():
    df = bars(5000, seed=246)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    s = np_sma(c, 44)
    up, dn = np_cross_over(c, s), np_cross_under(c, s)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    msgs, ok_all = [], True
    for mode in ("Both", "Long Only", "Short Only"):
        def orders(i, pos, mode=mode):
            out = []
            if up[i]:
                out.append(("entry", 1) if mode in ("Both", "Long Only") else ("close", -1))
            if dn[i]:
                out.append(("entry", -1) if mode in ("Both", "Short Only") else ("close", 1))
            return out

        ref = simulate(o, h, l, c, orders)
        ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Trade Direction": mode},
                                            strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
        ok_all = ok_all and ok and len(ref) > 10
        msgs.append(f"{mode}: {detail} ({len(ref)})")
    return ok_all, "; ".join(msgs)
