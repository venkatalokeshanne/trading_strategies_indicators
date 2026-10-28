"""Independent check — Keynes multi-timeframe (W6w1R6uB): 1h bars, long only, orders at the signal close (process_orders_on_close). keynes = 1.12*EMA5(100*(close-SMA240)/SMA240) - 0.48; a cross up through 0 with HMA217 rising
and the daily close (09:30-NY blocks, lookahead off) above the daily SMA60 of closes enters when flat (pyramiding 0 = one trade); a cross down closes it."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, np_periods, np_security_lookahead_off, np_sma, np_wma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "W6w1R6uB"


def check():
    df = bars(14000, seed=9, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sma240 = np_sma(c, 240)
    keynes = 1.12 * np_ema(100 * (c - sma240) / sma240, 5) - 0.48
    hma = np_wma(2 * np_wma(c, 108) - np_wma(c, 217), 15)
    hma_up = hma > np.r_[np.nan, hma[:-1]]
    pid, last_of = np_periods(df, 1440)
    dclose = np.array([c[last_of & (pid == p)][0] for p in range(pid[-1] + 1)])
    dclose_chart = np_security_lookahead_off(dclose, pid, last_of)
    dsma = np_security_lookahead_off(np_sma(dclose, 60), pid, last_of)
    with np.errstate(invalid="ignore"):
        up = np_cross_over(keynes, 0.0) & hma_up & (dclose_chart > dsma)
        dn = np_cross_under(keynes, 0.0)

    def orders(i, pos):
        out = []
        if up[i]:
            out.append(("entry", 1))
        if pos > 0 and dn[i]:
            out.append(("close", 1))
        return out

    ref = simulate(o, h, l, c, orders, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
