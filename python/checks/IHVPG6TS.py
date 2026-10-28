"""Independent check — Stop loss and Take Profit in $$ (IHVPG6TS): SMA 14/28 reversal. strategy.exit(profit, loss) in TICKS
is re-issued every bar while in a position: target = entry +/- money (1 share, pointvalue 1), stop = entry -/+ money, working
from the bar after the fill. The dollar inputs are scaled down (1.0 / 0.5) so the synthetic ~100-1000 prices hit them."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "IHVPG6TS"
TP, SL = 1.0, 0.5


def check():
    df = bars(20000, seed=87, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    f, s = np_sma(c, 14), np_sma(c, 28)
    up, dn = np_cross_over(f, s), np_cross_under(f, s)
    held = []                                          # position at each bar's close: the exit is only issued while one exists

    def orders(i, pos):
        held.append(pos != 0)
        return ([("entry", 1)] if up[i] else []) + ([("entry", -1)] if dn[i] else [])

    # an exit issued while the OLD position was open (held[i-1]) already covers a reversing entry on its fill bar
    active = lambda i, eb: i > eb or (i > 0 and held[i - 1])
    ref = simulate(o, h, l, c, orders,
                   stop=lambda i, pos, ep, eb: ep - pos * SL if active(i, eb) else None,
                   target=lambda i, pos, ep, eb: ep + pos * TP if active(i, eb) else None)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params={"Take Profit $$": TP, "Stop Loss $$": SL}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
