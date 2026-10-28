"""Independent check — Master Scalper (dsNewNEV): 5-min New York bars. Walls = session VWAP(hlc3) -/+ 2 * 5 * multiplier (multiplier scaled to the price level, passed to both sides); a bar with low <= lower wall * 1.001,
green, volume > 1.5 * SMA20(volume), close > EMA200 enters long (the mirror short), reversing, pyramiding 1. `time(...) != na` is IEEE-true everywhere, so the session never filters (as in Python / pinelib).
Exits are unconditional profit / loss in ticks around the fill price (tick 0.01), so they work from the fill bar. Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_ema, np_sma, np_vwap, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "dsNewNEV"
TICK = 0.01


def check():
    df = bars(60000, seed=227, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    vw = np_vwap(df, (h + l + c) / 3)
    dev = float(np.mean(np.abs(c - vw)))
    mult = round(dev * 1.2 / 10.0, 6)
    iv = 5.0 * mult
    lo_t, up_t = vw - iv * 2, vw + iv * 2
    spike = v > np_sma(v, 20) * 1.5
    e = np_ema(c, 200)
    tp_t = int(round(dev * 1.5 / TICK))
    sl_t = int(round(dev * 1.0 / TICK))
    with np.errstate(invalid="ignore"):
        bf = (l <= lo_t * 1.001) & (c > o) & spike & (c > e)
        sf = (h >= up_t * 0.999) & (c < o) & spike & (c < e)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if bf[i] else []) + ([("entry", -1)] if sf[i] else []),
                   stop=lambda i, pos, ep, eb: ep - pos * sl_t * TICK, target=lambda i, pos, ep, eb: ep + pos * tp_t * TICK)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params={"Global Vol Multiplier": mult, "Take Profit (Ticks)": tp_t, "Stop Loss (Ticks)": sl_t},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
