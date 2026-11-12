"""Independent check — XRP Price Action + Volume (FbxSjrcu): daily bars. EMA50 > EMA200 and a green close above the previous 20-bar highest high on volume > 1.5 * SMA20 enters long (mirror short), reversing, pyramiding 1.
Both exits are unconditional ATR stops (close -/+ 1.5 ATR14) re-issued every bar, so bar i works with bar i-1's level for its direction — also on a fill bar."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "FbxSjrcu"


def check():
    df = bars(8000, seed=243)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    f, s, vm, atr = np_ema(c, 50), np_ema(c, 200), np_sma(v, 20), np_atr(h, l, c, 14)
    hh = pd.Series(h).shift(1).rolling(20).max().to_numpy()
    ll = pd.Series(l).shift(1).rolling(20).min().to_numpy()
    with np.errstate(invalid="ignore"):
        bs = (f > s) & (c > hh) & (c > o) & (v > vm * 1.5)
        ss = (f < s) & (c < ll) & (c < o) & (v > vm * 1.5)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if bs[i] else []) + ([("entry", -1)] if ss[i] else []),
                   stop=lambda i, pos, ep, eb: None if (i == 0 or np.isnan(atr[i - 1])) else c[i - 1] - pos * atr[i - 1] * 1.5)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
