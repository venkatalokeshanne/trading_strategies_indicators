"""Independent check — SMA(4)/SMA(30) (KW2v4SNI): hourly bars, process_orders_on_close (fills at the signal close), long only. A cross of SMA4 over
SMA30 opens the long (if not already long); the cross back under closes it."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "KW2v4SNI"


def check():
    df = bars(12000, seed=132, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    s4, s30 = np_sma(c, 4), np_sma(c, 30)
    up, dn = np_cross_over(s4, s30), np_cross_under(s4, s30)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if up[i] and pos <= 0 else []) + ([("close", 1)] if dn[i] and pos > 0 else []),
                   on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
