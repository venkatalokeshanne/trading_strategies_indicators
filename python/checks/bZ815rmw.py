"""Independent check — Bot Acumulacion GGAL (bZ815rmw): daily bars, long only, 1 unit. Buy at the next open when EMA15 crosses over EMA30 and the bar is inside 2015-01-01 .. 2025-12-31 23:59:59 UTC. close_all (next open)
when EMA15 crosses under EMA60 with ADX14 > 20, or on the first bar after the period end with a position open; ignored when nothing is open at that script run. Margin and slippage off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_dmi, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "bZ815rmw"


def check():
    df = bars(5000, seed=359)
    t = df["time"].to_numpy()
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    m15, m30, m60 = np_ema(c, 15), np_ema(c, 30), np_ema(c, 60)
    _, _, adx = np_dmi(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        inp = (t >= 1420070400000) & (t <= 1767225599000)
        buy = np_cross_over(m15, m30) & inp
        sell = np_cross_under(m15, m60) & (adx > 20)

    def orders(i, pos):
        out = []
        if buy[i]:
            out.append(("entry", 1))
        if (sell[i] or (t[i] > 1767225599000 and pos > 0)) and pos > 0:
            out.append(("close", 1))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
