"""Independent check — RSI Mean Reversion (JFIZkwZR): daily bars. RSI(3) crossing over 40 closes the short (if shorts are allowed) and buys (if longs are allowed); crossing under 70 closes the long (if longs allowed) and sells short (if
shorts allowed). Run for Both / Long Only / Short Only."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "JFIZkwZR"


def check():
    df = bars(5000, seed=283)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    r = np_rsi(c, 3)
    up, dn = np_cross_over(r, 40.0), np_cross_under(r, 70.0)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    msgs, ok_all = [], True
    for mode in ("Both", "Long Only", "Short Only"):
        cl, cs = mode in ("Long Only", "Both"), mode in ("Short Only", "Both")

        def orders(i, pos, cl=cl, cs=cs):
            out = []
            if up[i]:
                if cs:
                    out.append(("close", -1))
                if cl:
                    out.append(("entry", 1))
            if dn[i]:
                if cl:
                    out.append(("close", 1))
                if cs:
                    out.append(("entry", -1))
            return out

        ref = simulate(o, h, l, c, orders)
        ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Trade Direction": mode},
                                            strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
        ok_all = ok_all and ok and len(ref) > 10
        msgs.append(f"{mode}: {detail} ({len(ref)})")
    return ok_all, "; ".join(msgs)
