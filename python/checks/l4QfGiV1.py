"""Independent check — 9/21 EMA + Volume Spike (l4QfGiV1): 5-min New York bars, long only (1 contract). EMA9 crossing over EMA21 on volume >= 1.5 * SMA20(volume) enters; EMA9 crossing under EMA21 on the same spike closes
at the next open. Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "l4QfGiV1"


def check():
    df = bars(30000, seed=248, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    f, s = np_ema(c, 9), np_ema(c, 21)
    with np.errstate(invalid="ignore"):
        hv = v >= np_sma(v, 20) * 1.5
    buy, sell = np_cross_over(f, s) & hv, np_cross_under(f, s) & hv
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if buy[i] else []) + ([("close", 1)] if sell[i] else []))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
