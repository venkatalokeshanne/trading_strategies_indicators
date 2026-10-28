"""Independent check — ATH / 52W Mechanical Breakout (2CKt3w9r): daily bars, long only. A high above the previous bar's N-bar high (N=250 here instead of 5000, passed to both sides) or above the PREVIOUS
chart bar's 52-week high (plain-pandas ISO weeks from the 09:30 session start, lookahead off) enters when flat. The ATR stop (0.5 ATR here instead of 2, passed to both sides) is rebuilt each bar from the highest high since
entry and issued only while long, so bar i works with bar i-1's value and only if a position existed at bar i-1's close. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "2CKt3w9r"
N, MULT = 250, 0.5


def check():
    df = bars(6000, seed=185)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    iso = (ny - pd.Timedelta(minutes=570)).dt.isocalendar()
    wk = (iso["year"].astype(int) * 100 + iso["week"].astype(int)).to_numpy()
    last_of = np.r_[wk[1:] != wk[:-1], True]
    pid = np.cumsum(np.r_[True, wk[1:] != wk[:-1]]) - 1
    wh = pd.Series(h).groupby(pid).max().to_numpy()
    w52 = pd.Series(wh).rolling(52).max().to_numpy()
    weekly = np.full(n, np.nan)
    for j in range(n):
        p = pid[j] if last_of[j] else pid[j] - 1
        if p >= 0:
            weekly[j] = w52[p]
    ath = pd.Series(h).rolling(N).max().to_numpy()
    ath1, wk1 = np.r_[np.nan, ath[:-1]], np.r_[np.nan, weekly[:-1]]
    with np.errstate(invalid="ignore"):
        go = (h > ath1) | (h > wk1)
    atr = np_atr(h, l, c, 14)
    poscl, hse, cur = np.zeros(n), np.full(n, np.nan), [np.nan]

    def orders(i, pos):
        poscl[i] = pos
        if pos > 0:
            cur[0] = h[i] if np.isnan(cur[0]) else max(cur[0], h[i])
        else:
            cur[0] = np.nan
        hse[i] = cur[0]
        return [("entry", 1)] if go[i] and pos == 0 else []

    def stop(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] <= 0 or np.isnan(hse[i - 1]):
            return None
        return hse[i - 1] - atr[i - 1] * MULT

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop)
    sym = SymbolInfo.make("AMEX:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"ATH Lookback Bars": N, "ATR Multiplier": MULT},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
