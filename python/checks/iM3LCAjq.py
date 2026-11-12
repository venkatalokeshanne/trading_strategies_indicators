"""Independent check — XAU Tanner Vol Funnel (iM3LCAjq): 5-min bars, long only. Close falling back under the upper Bollinger band (25, 2) after
closing above it, RSI>55 and ATR>0.8*SMA(ATR,50); only when flat. While long: limit +2.5 % / stop -1.2 % of the average price, re-issued every
bar (works from the bar after the fill)."""
import numpy as np

from indep import bars, compare, np_atr, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "iM3LCAjq"


def check():
    df = bars(20000, seed=114, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    basis = np_sma(c, 25)
    sd = np.full(n, np.nan)
    for i in range(24, n):
        sd[i] = np.std(c[i - 24:i + 1])                      # Pine's stdev is the population one
    upper = basis + 2.0 * sd
    rsi, atr = np_rsi(c, 14), np_atr(h, l, c, 14)
    vol_ok = atr > np_sma(atr, 50) * 0.8
    pc, pu = np.r_[np.nan, c[:-1]], np.r_[np.nan, upper[:-1]]
    with np.errstate(invalid="ignore"):
        sig = (pc > pu) & (c < upper) & (rsi > 55) & vol_ok
    ref = simulate(o, h, l, c, lambda i, pos: [("entry", 1)] if sig[i] and pos == 0 else [],
                   stop=lambda i, pos, ep, eb: ep * (1 - 0.012) if i > eb else None,
                   target=lambda i, pos, ep, eb: ep * (1 + 0.025) if i > eb else None)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
