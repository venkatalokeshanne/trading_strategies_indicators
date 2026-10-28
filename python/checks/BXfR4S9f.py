"""Independent check — Pro-Swing Guard (BXfR4S9f): hourly bars. SuperTrend(10, 5) up-trend with the close above a rising EMA200 buys; with shorts enabled
(passed to both sides to cover the mirrored branch) a down-trend below a falling EMA200 sells short; a SuperTrend flip closes the open trade."""
import numpy as np

from indep import bars, compare, np_ema, np_supertrend, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "BXfR4S9f"


def check():
    df = bars(20000, seed=135, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    _, d = np_supertrend(h, l, c, 5.0, 10)
    e = np_ema(c, 200)
    pe = np.r_[np.nan, e[:-1]]
    with np.errstate(invalid="ignore"):
        lg = (d < 0) & (c > e) & (e > pe)
        sg = (d > 0) & (c < e) & (e < pe)

    def orders(i, pos):
        out = []
        if lg[i]:
            out.append(("entry", 1))
        if sg[i]:
            out.append(("entry", -1))
        if pos > 0 and d[i] > 0:
            out.append(("close", 1))
        if pos < 0 and d[i] < 0:
            out.append(("close", -1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", params={"Enable Short Trades?": True}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
