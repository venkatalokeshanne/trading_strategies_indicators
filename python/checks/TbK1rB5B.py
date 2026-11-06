"""Independent check — TrendShift Supertrend + Regime Switch (TbK1rB5B): daily bars, one position (flips reverse), trade list only. ADX14/14 regime: > 25 trending (multiplier 1.75), < 20 choppy (4.5), otherwise the last multiplier is kept
(starts at 1.75). SuperTrend on hl2 with ATR10 and that per-bar multiplier (the usual Pine ratchet, direction -1 = up). A direction change to -1 goes long, to +1 goes short, but nothing new is entered while ADX < 20. Defaults: no trailing exit,
no max-bars, no flatten. Margin and slippage off on the pinelib side; the risk-sized quantity does not change the trade list."""
import numpy as np

from indep import bars, compare, np_dmi, np_supertrend, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "TbK1rB5B"


def check():
    df = bars(7000, seed=363)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    _, _, adx = np_dmi(h, l, c, 14)
    mult = np.full(n, 1.75)
    cur, regime_mult = 1.75, 1.75
    for i in range(n):
        with np.errstate(invalid="ignore"):
            if adx[i] > 25:
                regime_mult = 1.75
            elif adx[i] < 20:
                regime_mult = 4.5
        mult[i] = regime_mult
    line, d = np_supertrend(h, l, c, mult, 10)
    chg = d - np.r_[np.nan, d[:-1]]
    with np.errstate(invalid="ignore"):
        choppy = adx < 20
        ls = (chg != 0) & (d == -1) & ~choppy
        ss = (chg != 0) & (d == 1) & ~choppy

    def orders(i, pos):
        out = []
        if ls[i] and pos <= 0:
            out.append(("entry", 1))
        if ss[i] and pos >= 0:
            out.append(("entry", -1))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
