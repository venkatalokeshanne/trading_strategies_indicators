"""Independent check — EMA9 + VWAP ATR trailing (EHADtuFr): 5-min bars, process_orders_on_close (fills at the signal close).
EMA9 crossing session VWAP(close) reverses the position; the exit order is re-issued every bar with trail_points =
trail_offset = ATR*2 read as TICKS (mintick 0.01), working from the bar after the fill. Uses indep.exit_hit's trailing model."""
import numpy as np

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_ema, np_vwap, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "EHADtuFr"


def check():
    df = bars(20000, seed=83, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    e9, vw, atr = np_ema(c, 9), np_vwap(df, c), np_atr(h, l, c, 14)
    up, dn = np_cross_over(e9, vw), np_cross_under(e9, vw)

    def trail(i, pos, ep, eb):
        if i <= eb or np.isnan(atr[i - 1]):
            return None
        return (atr[i - 1] * 2, atr[i - 1] * 2)

    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if up[i] else []) + ([("entry", -1)] if dn[i] else []),
                   trail=trail, tick=0.01, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
