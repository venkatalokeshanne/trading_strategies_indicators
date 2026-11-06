"""Independent check — 9:30 NY reference candle (fq3Es1YA): 5-min New York bars, process_orders_on_close. The bar starting in 09:30-09:35 gives the day's reference high / low (reset at the first bar of each trading day, days
from 09:30); 09:36-15:50, once per day, a close above / below it enters long / short at that close; SL distance = max(reference range, 1500 ticks) with mintick scaled to the price level (passed to both sides), stop at the
reference level -/+ distance, target 2 distances beyond it, issued with the entry (works from the bar after the fill); a repeat signal on the open side re-issues the exit. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_periods, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "fq3Es1YA"


def check():
    df = bars(40000, seed=244, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    ref_bar = (m >= 570) & (m < 575)
    win = (m >= 576) & (m < 950)
    day, _ = np_periods(df, 1440)
    tick = round(float(c.mean()) * 0.0004, 6)
    min_sl = 1500 * tick
    hi = lo = np.nan
    cnt = [0]
    lvl = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}

    def orders(i, pos):
        nonlocal hi, lo
        if i > 0 and day[i] != day[i - 1]:
            cnt[0] = 0
            hi = lo = np.nan
        if ref_bar[i]:
            hi = h[i] if np.isnan(hi) else max(hi, h[i])
            lo = l[i] if np.isnan(lo) else min(lo, l[i])
        out = []
        sd = max(hi - lo, min_sl) if not (np.isnan(hi) or np.isnan(lo)) else np.nan
        ok = win[i] and cnt[0] == 0
        if ok and c[i] > hi:
            out.append(("entry", 1)); lvl[1] = (hi - sd, hi + sd * 2.0); cnt[0] = 1
        if ok and c[i] < lo:
            out.append(("entry", -1)); lvl[-1] = (lo + sd, lo - sd * 2.0); cnt[0] = 1
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, on_close=True, stop=lambda i, pos, ep, eb: lvl[pos][0], target=lambda i, pos, ep, eb: lvl[pos][1])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9, mintick=tick)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
