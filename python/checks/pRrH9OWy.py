"""Independent check — EMA Golden/Dead Cross (pRrH9OWy; Rn9YffSm is the same script): daily bars. EMA50 over EMA200 (golden cross) closes the short then goes long; under (dead cross) closes the long then goes short; "Long Only" /
"Short Only" suppress the other side's pair. Run for all three Trade Direction settings. Margin off on the pinelib side (100 % of equity)."""
from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "pRrH9OWy"
SEED = 255


def build(tv_id, seed):
    df = bars(5000, seed=seed)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    f, s = np_ema(c, 50), np_ema(c, 200)
    gc, dc = np_cross_over(f, s), np_cross_under(f, s)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    msgs, ok_all = [], True
    for mode in ("Both", "Long Only", "Short Only"):
        def orders(i, pos, mode=mode):
            out = []
            if gc[i] and mode in ("Both", "Long Only"):
                out += [("close", -1), ("entry", 1)]
            if dc[i] and mode in ("Both", "Short Only"):
                out += [("close", 1), ("entry", -1)]
            return out

        ref = simulate(o, h, l, c, orders)
        ok, detail = compare(run_conversion(tv_id, df, symbol=sym, tf="D", params={"Trade Direction": mode},
                                            strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
        ok_all = ok_all and ok and (len(ref) > 3 or mode != "Both")     # one-sided modes never close, so they only complete trades when a close exists
        msgs.append(f"{mode}: {detail} ({len(ref)})")
    return ok_all, "; ".join(msgs)


def check():
    return build(TV_ID, SEED)
