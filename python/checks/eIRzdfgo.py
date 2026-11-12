"""Independent check — BTC V4 Multi-Engine (eIRzdfgo): 5-min New York bars. Higher-timeframe vote: for the 30 / 60 / 240-minute and daily bars (plain-pandas blocks from 09:30, lookahead off), +1 when EMA20 > EMA50 > EMA200 of the
block closes, -1 when stacked down; >= 3 agreeing votes. On the chart: stacked EMAs + vote, and a pullback (previous candle red above EMA20[1] and ATR14 > SMA14(ATR)) or a strong breakout candle (close beyond the previous
high / low by more than ATR range), not more than 1 % beyond EMA20, enters when flat; entry + exit (stop = bar low / high -/+ 0.2 %, 2 R target) are issued on the signal bar, so the bracket works from the fill bar.
Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_periods, np_security_lookahead_off, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "eIRzdfgo"


def trend(df, c, minutes):
    pid, last_of = np_periods(df, minutes)
    hc = pd.Series(c).groupby(pid).last().to_numpy()
    e20, e50, e200 = (np_security_lookahead_off(np_ema(hc, k), pid, last_of) for k in (20, 50, 200))
    with np.errstate(invalid="ignore"):
        return np.where((e20 > e50) & (e50 > e200), 1, np.where((e20 < e50) & (e50 < e200), -1, 0))


def check():
    df = bars(100000, seed=275, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ts = [trend(df, c, m) for m in (30, 60, 240, 1440)]
    bull_htf = sum((t == 1).astype(int) for t in ts) >= 3
    bear_htf = sum((t == -1).astype(int) for t in ts) >= 3
    e20, e50, e200 = np_ema(c, 20), np_ema(c, 50), np_ema(c, 200)
    atr = np_atr(h, l, c, 14)
    c1, o1, h1, l1, e20p = (np.r_[np.nan, x[:-1]] for x in (c, o, h, l, e20))
    with np.errstate(invalid="ignore"):
        bt, st_ = (e20 > e50) & (e50 > e200), (e20 < e50) & (e50 < e200)
        vol_ok = atr > np_sma(atr, 14)
        rng = h - l
        sbull, sbear = (c > h1) & (rng > atr), (c < l1) & (rng > atr)
        pl, ps = (c1 < o1) & (c1 > e20p), (c1 > o1) & (c1 < e20p)
        ll, ls_ = c > e20 * 1.01, c < e20 * 0.99
        buy = bt & bull_htf & ((vol_ok & pl) | sbull) & ~ll
        sell = st_ & bear_htf & ((vol_ok & ps) | sbear) & ~ls_
    lvl = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}

    def orders(i, pos):
        out = []
        if buy[i] and pos == 0:
            sl = l[i] * (1 - 0.2 / 100)
            out.append(("entry", 1)); lvl[1] = (sl, c[i] + (c[i] - sl) * 2.0)
        if sell[i] and pos == 0:
            sl = h[i] * (1 + 0.2 / 100)
            out.append(("entry", -1)); lvl[-1] = (sl, c[i] - (sl - c[i]) * 2.0)
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: lvl[pos][0], target=lambda i, pos, ep, eb: lvl[pos][1])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
