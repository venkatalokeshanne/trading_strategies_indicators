"""Independent check — Super RSI Strategy (N9XkAE0B): hourly bars. Supertrend(3, 10) up-trend with RSI>50 buys, down-trend with
RSI<50 sells short (every bar the condition holds; same-direction re-entries are ignored); RSI>70 closes the long, RSI<30 the short."""
import numpy as np

from indep import bars, compare, np_rsi, np_supertrend, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "N9XkAE0B"


def check():
    df = bars(12000, seed=99, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    _, d = np_supertrend(h, l, c, 3.0, 10)
    rsi = np_rsi(c, 14)
    with np.errstate(invalid="ignore"):
        buy, sell = (d < 0) & (rsi > 50), (d > 0) & (rsi < 50)
        cl_long, cl_short = rsi > 70, rsi < 30

    def orders(i, pos):
        out = []
        if buy[i]:
            out.append(("entry", 1))
        if sell[i]:
            out.append(("entry", -1))
        if cl_long[i] and pos > 0:                    # strategy.close(id) only acts on a trade that is already open
            out.append(("close", 1))
        if cl_short[i] and pos < 0:
            out.append(("close", -1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
