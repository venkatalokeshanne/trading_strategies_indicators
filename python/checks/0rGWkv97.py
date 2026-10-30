"""Independent check — Undertow Backtest (0rGWkv97): daily bars, bounds -20 / +30 here (passed to both sides). WaveTrend on hlc3: esa = EMA9, de = EMA9(|ap-esa|), ci = (ap-esa)/(0.015 de), wt1 = EMA12(ci), wt2 = SMA3(wt1).
A cross up with wt2 <= oversold buys (one trade at a time); a cross down with wt2 >= overbought closes it; next-open fills."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "0rGWkv97"
OB, OS = 30, -20


def check():
    df = bars(8000, seed=27)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    ap = (h + l + c) / 3
    esa = np_ema(ap, 9)
    de = np_ema(np.abs(ap - esa), 9)
    ci = (ap - esa) / (0.015 * de)
    wt1 = np_ema(ci, 12)
    wt2 = np_sma(wt1, 3)
    with np.errstate(invalid="ignore"):
        buy = np_cross_over(wt1, wt2) & (wt2 <= OS)
        sell = np_cross_under(wt1, wt2) & (wt2 >= OB)

    def orders(i, pos):
        out = []
        if buy[i]:
            out.append(("entry", 1))
        if sell[i] and pos > 0:
            out.append(("close", 1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Overbought Bound (strong sell)": OB, "Oversold Bound (strong buy)": OS},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
