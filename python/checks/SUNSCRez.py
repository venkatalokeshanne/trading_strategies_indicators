"""Independent check — Ema Crosses Strategy (SUNSCRez): 5-min bars. EMA 9/26 cross reverses (close of the other side, then entry);
both exits are unconditional with absolute 20-point stop / 40-point target around the position's average price as of the previous
bar's close (na while flat), for BOTH directions, so a reversal's first bar uses the OLD average. close(id) acts only on an open trade."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "SUNSCRez"


def check():
    df = bars(20000, seed=107, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    f, s = np_ema(c, 9), np_ema(c, 26)
    up, dn = np_cross_over(f, s), np_cross_under(f, s)
    ep_now, avg_close = {}, np.full(n, np.nan)

    def orders(i, pos):
        avg_close[i] = ep_now.get(i, np.nan) if pos != 0 else np.nan
        out = []
        if up[i] and pos <= 0:
            if pos < 0:
                out.append(("close", -1))
            out.append(("entry", 1))
        if dn[i] and pos >= 0:
            if pos > 0:
                out.append(("close", 1))
            out.append(("entry", -1))
        return out

    def level(k):
        def f_(i, pos, ep, eb):
            ep_now[i] = ep
            if i == 0 or np.isnan(avg_close[i - 1]):
                return None
            a = avg_close[i - 1]
            return (a - 20.0 if pos > 0 else a + 20.0) if k == 0 else (a + 40.0 if pos > 0 else a - 40.0)
        return f_

    ref = simulate(o, h, l, c, orders, stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
