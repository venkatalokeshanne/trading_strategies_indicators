"""Independent check — Turtle Trading System 2 (jaZexIkA / jaZexIkA are the same script): daily bars, pyramiding 4 (indep.simulate_pyr, one unit per lot; sizes do not change entries / exits). Entry: the close crosses over the previous bar's 55-bar highest high
(under the 55-bar lowest low for shorts) while flat -> unit 1 (entry price = that close) with a stop 2 ATR20 beyond it, placed with the entry (works from the fill bar). While in the position a new unit is added each time the close is at least
entry + units x 0.5 ATR (mirrored for shorts) after a unit is counted, with a general stop 2 ATR20 from that close re-issued for all lots. The effective stop is the one issued last (it ratchets in the trend; the first unit's own stop is no tighter
here). The close crossing under the previous bar's 20-bar low (over the high) closes everything at the next open. Margin and slippage off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, run_conversion, simulate_pyr
from pinelib import SymbolInfo

TV_ID = "jaZexIkA"


def check():
    df = bars(8000, seed=156)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr = np_atr(h, l, c, 20)
    sh = lambda x: np.r_[np.nan, x[:-1]]
    eh = sh(pd.Series(h).rolling(55, min_periods=55).max().to_numpy())
    el = sh(pd.Series(l).rolling(55, min_periods=55).min().to_numpy())
    xl = sh(pd.Series(l).rolling(20, min_periods=20).min().to_numpy())
    xh = sh(pd.Series(h).rolling(20, min_periods=20).max().to_numpy())
    with np.errstate(invalid="ignore"):
        le, se = np_cross_over(c, eh), np_cross_under(c, el)
        lx, sx = np_cross_under(c, xl), np_cross_over(c, xh)
    S = dict(ep=np.nan, units=0, stop={1: None, -1: None}, first={1: None, -1: None})

    def orders(i, pos):
        out = []
        if pos == 0:
            S["units"] = 0
            S["ep"] = np.nan
        if le[i] and pos == 0:
            out.append(("entry", 1))
            S.update(ep=c[i], units=1)
            S["stop"][1] = c[i] - 2.0 * atr[i]
        if pos > 0 and S["units"] < 4 and not np.isnan(S["ep"]) and c[i] >= S["ep"] + S["units"] * 0.5 * atr[i]:
            out.append(("entry", 1))
            S["units"] += 1
            S["stop"][1] = c[i] - 2.0 * atr[i]
        if lx[i] and pos > 0:
            out.append(("close_all",))
            S.update(units=0, ep=np.nan)
        if se[i] and pos == 0:
            out.append(("entry", -1))
            S.update(ep=c[i], units=1)
            S["stop"][-1] = c[i] + 2.0 * atr[i]
        if pos < 0 and S["units"] < 4 and not np.isnan(S["ep"]) and c[i] <= S["ep"] - S["units"] * 0.5 * atr[i]:
            out.append(("entry", -1))
            S["units"] += 1
            S["stop"][-1] = c[i] + 2.0 * atr[i]
        if sx[i] and pos < 0:
            out.append(("close_all",))
            S.update(units=0, ep=np.nan)
        return out

    def stop(i, d, trades):
        return S["stop"][d]

    with np.errstate(invalid="ignore"):
        ref = simulate_pyr(o, h, l, c, orders, pyramiding=4, stop=stop)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "default_qty_value": 5}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
