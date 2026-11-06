"""Independent check — Multi-TF Signal Bot v2 (ASHXoH1O): 5-min New York bars. EMA 9/21 cross; longs also need RSI<70 and the hourly EMA9 above the hourly
EMA21 (plain-pandas 60-minute blocks, lookahead off: last chart bar of the hour = that hour, earlier bars = previous hour); shorts need RSI>30.
Exits are unconditional: bar i works with bar i-1's close * 0.985 / 1.03 (long) and * 1.015 / 0.97 (short), also on the fill bar."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, np_periods, np_rsi, np_security_lookahead_off, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "ASHXoH1O"


def check():
    df = bars(20000, seed=119, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    f, s, rsi = np_ema(c, 9), np_ema(c, 21), np_rsi(c, 14)
    pid, last_of = np_periods(df, 60)
    hc = pd.Series(c).groupby(pid).last().to_numpy()
    hf = np_security_lookahead_off(np_ema(hc, 9), pid, last_of)
    hs = np_security_lookahead_off(np_ema(hc, 21), pid, last_of)
    with np.errstate(invalid="ignore"):
        lg = np_cross_over(f, s) & (rsi < 70) & (hf > hs)
        sg = np_cross_under(f, s) & (rsi > 30)

    def stop(i, pos, ep, eb):
        return None if i == 0 else c[i - 1] * (0.985 if pos > 0 else 1.015)

    def target(i, pos, ep, eb):
        return None if i == 0 else c[i - 1] * (1.03 if pos > 0 else 0.97)

    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if lg[i] else []) + ([("entry", -1)] if sg[i] else []),
                   stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
