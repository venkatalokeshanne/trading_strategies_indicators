"""Independent check — Webhook Alert Strategy Template (zrDoqm9F): daily bars, MA type WMA (passed to both sides, covers the switch), slippage 0, orders at the signal close (process_orders_on_close). Fast WMA20 crossing WMA50 (over: long; under: short) while not already on that side enters (reversing) with stop = close -/+ 1.5 ATR14 and
target = 2 x that distance, fixed on the signal bar (also replacing the bracket when already in the trade)."""
import numpy as np

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_wma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "zrDoqm9F"


def check():
    df = bars(9000, seed=33)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    f, s, atr = np_wma(c, 20), np_wma(c, 50), np_atr(h, l, c, 14)
    up, dn = np_cross_over(f, s), np_cross_under(f, s)
    lvl = {}

    def orders(i, pos):
        out = []
        d = atr[i] * 1.5
        if up[i] and pos <= 0:
            out.append(("entry", 1))
            lvl[1] = (c[i] - d, c[i] + 2 * d)
        if dn[i] and pos >= 0:
            out.append(("entry", -1))
            lvl[-1] = (c[i] + d, c[i] - 2 * d)
        return out

    def stop(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][0]

    def target(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"MA type": "WMA"},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
