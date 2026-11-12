"""Independent check — Position size based on risk (hoCPm5UY): 5-min bars. A long is ordered at every bar_index % 333 == 0 and a short at
% 444 == 0 (reversing, same-direction repeats ignored). strategy.exit(loss = 10 % of the average price, in ticks) is issued each bar
while a position exists (na while flat): bar i works with the average price held at bar i-1's close, which is the OLD position's
average on a reversal's first bar. Quantity does not change prices; margin 10 % never binds."""
import numpy as np

from indep import bars, compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "hoCPm5UY"


def check():
    df = bars(9000, seed=109, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ep_now, avg_close = {}, np.full(n, np.nan)

    def orders(i, pos):
        avg_close[i] = ep_now.get(i, np.nan) if pos != 0 else np.nan
        return ([("entry", 1)] if i % 333 == 0 else []) + ([("entry", -1)] if i % 444 == 0 else [])

    def stop(i, pos, ep, eb):
        ep_now[i] = ep
        if i == 0 or np.isnan(avg_close[i - 1]):
            return None
        d = avg_close[i - 1] * 0.10
        return ep - d if pos > 0 else ep + d

    ref = simulate(o, h, l, c, orders, stop=stop)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
