"""Independent check — ATH / 52W High Breakout (HQ14VsdY): daily bars, long only. Entry when the close exceeds the PRIOR bar's
all-time high (running max of highs) or the PRIOR chart bar's 52-week high, where the weekly series is built with plain pandas
(ISO weeks counted from the 09:30 session start; rolling max of weekly highs over 52 weeks) and, with lookahead off, a week's value
shows on its last chart bar and the previous week's value before that. Exit: stop = average price - MULT ATR, re-issued every bar
(na while flat), working from the bar after the fill. Margin off on the pinelib side (100 % of equity, LESSONS P12)."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "HQ14VsdY"
MULT = 0.3          # tighter than the 2.0 default so the stop fires often enough to compare (passed to both sides)


def check():
    df = bars(6000, seed=103)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    sh = ny.dt.tz_localize(None) - pd.Timedelta(minutes=570)
    iso = sh.dt.isocalendar()
    wk = (iso["year"].astype(int) * 100 + iso["week"].astype(int)).to_numpy()
    new_wk = np.r_[True, wk[1:] != wk[:-1]]
    last_of = np.r_[wk[1:] != wk[:-1], True]
    pid = np.cumsum(new_wk) - 1
    wh = pd.Series(h).groupby(pid).max().to_numpy()                    # weekly highs
    w52 = pd.Series(wh).rolling(52).max().to_numpy()                   # ta.highest(high, 52) on the weekly bars
    weekly = np.full(n, np.nan)
    for j in range(n):
        p = pid[j] if last_of[j] else pid[j] - 1                        # lookahead off
        if p >= 0:
            weekly[j] = w52[p]
    ath = np.maximum.accumulate(h)
    ath1, weekly1 = np.r_[np.nan, ath[:-1]], np.r_[np.nan, weekly[:-1]]
    with np.errstate(invalid="ignore"):
        go = (c > ath1) | (c > weekly1)
    atr = np_atr(h, l, c, 14)
    ref = simulate(o, h, l, c, lambda i, pos: [("entry", 1)] if go[i] else [],
                   stop=lambda i, pos, ep, eb: ep - MULT * atr[i - 1] if i > eb else None)
    sym = SymbolInfo.make("AMEX:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"ATR Multiplier": MULT}, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
