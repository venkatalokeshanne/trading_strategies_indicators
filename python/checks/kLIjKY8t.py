"""Independent check — EMA Cross + Triple VWAP Reclaim (kLIjKY8t): 5-min New York bars. EMA9/20 cross + reclaim of the session VWAP (lowest low / highest high of 10 bars beyond VWAP, close back across) + 60-minute filter (hourly
close vs hourly EMA20 and hourly session VWAP; hourly ATR14 sizes the bracket): plain-pandas 60-minute blocks from the 09:30 session start, lookahead off (a block's value on its last chart bar, the previous block's before that).
The signal bar issues entry + exit (stop = close -/+ 0.5 hourly ATR, limit = 1 R), so the bracket works from the fill bar; a repeat signal on the open side replaces the levels. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_ema, np_periods, np_security_lookahead_off, np_vwap, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "kLIjKY8t"


def check():
    df = bars(60000, seed=215, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    pid, last_of = np_periods(df, 60)
    g = pd.DataFrame({"pid": pid, "time": df["time"], "open": o, "high": h, "low": l, "close": c, "volume": df["volume"]}).groupby("pid")
    hdf = pd.DataFrame({"time": g["time"].first(), "open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                        "close": g["close"].last(), "volume": g["volume"].sum()}).reset_index(drop=True)
    hc, hh, hl = hdf["close"].to_numpy(), hdf["high"].to_numpy(), hdf["low"].to_numpy()
    h_close = np_security_lookahead_off(hc, pid, last_of)
    h_ema = np_security_lookahead_off(np_ema(hc, 20), pid, last_of)
    h_vw = np_security_lookahead_off(np_vwap(hdf, hc), pid, last_of)
    h_atr = np_security_lookahead_off(np_atr(hh, hl, hc, 14), pid, last_of)
    vw = np_vwap(df, c)
    lo = pd.Series(l).rolling(10).min().to_numpy()
    hi = pd.Series(h).rolling(10).max().to_numpy()
    e9, e20 = np_ema(c, 9), np_ema(c, 20)
    with np.errstate(invalid="ignore"):
        lg = np_cross_over(e9, e20) & (h_close > h_ema) & (h_close > h_vw) & (lo < vw) & (c > vw)
        sg = np_cross_under(e9, e20) & (h_close < h_ema) & (h_close < h_vw) & (hi > vw) & (c < vw)
    lvl = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}

    def orders(i, pos):
        out = []
        sd = h_atr[i] * 0.5
        if lg[i]:
            out.append(("entry", 1)); lvl[1] = (c[i] - sd, c[i] + sd)
        if sg[i]:
            out.append(("entry", -1)); lvl[-1] = (c[i] + sd, c[i] - sd)
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: lvl[pos][0], target=lambda i, pos, ep, eb: lvl[pos][1])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
