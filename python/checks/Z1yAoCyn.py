"""Independent check — CNPS2 Bollinger Band (Z1yAoCyn): 5-min bars. Close above the upper Bollinger band (20, 2) buys, below the lower band sells short
(reversing); a long closes when the close falls under the lower band, a short when it rises over the upper one (close() acts only on an open trade).
Both 10-point stops are unconditional around the position's average price as of the previous close (na while flat; OLD average on a reversal's first bar)."""
import numpy as np

from indep import bars, compare, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "Z1yAoCyn"


def check():
    df = bars(20000, seed=130, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    basis = np_sma(c, 20)
    sd = np.full(n, np.nan)
    for i in range(19, n):
        sd[i] = np.std(c[i - 19:i + 1])
    up, lo = basis + 2.0 * sd, basis - 2.0 * sd
    with np.errstate(invalid="ignore"):
        lg, sg = c > up, c < lo
    ep_now, avg_close = {}, np.full(n, np.nan)

    def orders(i, pos):
        avg_close[i] = ep_now.get(i, np.nan) if pos != 0 else np.nan
        out = []
        if lg[i]:
            out.append(("entry", 1))
        if sg[i]:
            out.append(("entry", -1))
        if pos > 0 and lo[i] > c[i]:
            out.append(("close", 1))
        if pos < 0 and up[i] < c[i]:
            out.append(("close", -1))
        return out

    def stop(i, pos, ep, eb):
        ep_now[i] = ep
        if i == 0 or np.isnan(avg_close[i - 1]):
            return None
        return avg_close[i - 1] - 10.0 if pos > 0 else avg_close[i - 1] + 10.0

    ref = simulate(o, h, l, c, orders, stop=stop)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
