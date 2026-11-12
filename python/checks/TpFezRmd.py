"""Independent check — AS 1M SMART MONEY STRATEGY (TpFezRmd): 5-min bars (24h synthetic incl. weekends), one position, reversals allowed. Score = [close > SMA50 > SMA500] + [close crosses over SMA7] + [low > high 2 bars ago] +
[low sweeps below the previous bar's 15-bar low and closes back above it] (mirror for short); score >= 3 with ATR5 > ATR14, BB(20,2) width not within 10% of its 50-bar low, Mon-Fri 09:30-16:00 New York bar time. On every
signal bar the stop / limit (1.5 / 2.5 ATR14 from that close) are re-issued for that side (also when the side is already open), working from the next bar. Margin, slippage off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "TpFezRmd"


def check():
    df = bars(40000, seed=1013, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    wd = ny.dt.dayofweek.to_numpy()                      # Mon=0
    us = (m >= 570) & (m < 960) & (wd <= 4)
    s9, s50, s500 = np_sma(c, 7), np_sma(c, 50), np_sma(c, 500)
    atr, atr5 = np_atr(h, l, c, 14), np_atr(h, l, c, 5)
    basis = np_sma(c, 20)
    dev = pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    width = (basis + 2 * dev - (basis - 2 * dev)) / basis
    low50 = pd.Series(width).rolling(50).min().to_numpy()
    sh = pd.Series(h).rolling(15).max().to_numpy()
    sl = pd.Series(l).rolling(15).min().to_numpy()
    sh1, sl1 = np.r_[np.nan, sh[:-1]], np.r_[np.nan, sl[:-1]]
    h2, l2 = np.r_[np.nan, np.nan, h[:-2]], np.r_[np.nan, np.nan, l[:-2]]
    with np.errstate(invalid="ignore"):
        valid = (atr5 > atr) & ~(width < low50 * 1.1)
        ls_hi = (h > sh1) & (c < sh1)
        ls_lo = (l < sl1) & (c > sl1)
        bf, sf = l > h2, h < l2
        bt, st_ = (c > s50) & (s50 > s500), (c < s50) & (s50 < s500)
        score_l = bt.astype(int) + np_cross_over(c, s9).astype(int) + bf.astype(int) + ls_lo.astype(int)
        score_s = st_.astype(int) + np_cross_under(c, s9).astype(int) + sf.astype(int) + ls_hi.astype(int)
        lsig = (score_l >= 3) & valid & us
        ssig = (score_s >= 3) & valid & us
    lv = {1: None, -1: None}

    def orders(i, pos):
        out = []
        if lsig[i]:
            out.append(("entry", 1))
            lv[1] = (c[i] - 1.5 * atr[i], c[i] + 2.5 * atr[i])
        if ssig[i]:
            out.append(("entry", -1))
            lv[-1] = (c[i] + 1.5 * atr[i], c[i] - 2.5 * atr[i])
        return out

    def stop(i, pos, ep, eb):
        return lv[pos][0] if lv[pos] else None

    def target(i, pos, ep, eb):
        return lv[pos][1] if lv[pos] else None

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "default_qty_value": 5}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
