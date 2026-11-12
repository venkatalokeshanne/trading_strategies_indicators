"""Independent check — RSI Range Compression (dwgn7hrE): daily bars, slippage 0. rsiRange = highest(RSI14, 20) - lowest(RSI14, 20); percentrank over 100 = 100 * (number of the previous 100 values <= current)/100; squeeze = rank <= 20; squeezeRecent = barssince(squeeze) <= 5.
Long when flat: RSI crosses over the previous bar's 20-bar RSI high, squeezeRecent, EMA50 > EMA50[5], ADX14 >= 15; short: RSI crosses under the previous 20-bar RSI low, EMA50 < EMA50[5]. Stop = close -/+ 2 ATR14 (distance d); long target = close + (close - d) * 2 (the source multiplies the stop PRICE),
short target = close - 2 d; all fixed at the signal bar."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_dmi, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "dwgn7hrE"


def check():
    df = bars(9000, seed=99)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    rsi = np_rsi(c, 14)
    rh = pd.Series(rsi).rolling(20).max().to_numpy()
    rl = pd.Series(rsi).rolling(20).min().to_numpy()
    rng = rh - rl
    rank = np.full(n, np.nan)
    for i in range(100, n):
        w = rng[i - 100:i]
        if not np.isnan(rng[i]) and not np.isnan(w).any():
            rank[i] = 100.0 * (w <= rng[i]).sum() / 100
    with np.errstate(invalid="ignore"):
        sq = rank <= 20
    since = np.full(n, np.nan)
    last = None
    for i in range(n):
        if sq[i]:
            last = i
        since[i] = np.nan if last is None else i - last
    ema = np_ema(c, 50)
    ema5 = np.r_[[np.nan] * 5, ema[:-5]]
    dp, dm, adx = np_dmi(h, l, c, 14)
    atr = np_atr(h, l, c, 14)
    rh1, rl1 = np.r_[np.nan, rh[:-1]], np.r_[np.nan, rl[:-1]]
    with np.errstate(invalid="ignore"):
        recent = since <= 5
        lt = np_cross_over(rsi, rh1) & recent & (ema > ema5) & (adx >= 15)
        st_ = np_cross_under(rsi, rl1) & recent & (ema < ema5) & (adx >= 15)
    lvl = {}

    def orders(i, pos):
        out = []
        d = atr[i] * 2.0
        if lt[i] and pos == 0:
            out.append(("entry", 1))
            lvl[1] = (c[i] - d, c[i] + (c[i] - d) * 2.0)
        if st_[i] and pos == 0:
            out.append(("entry", -1))
            lvl[-1] = (c[i] + d, c[i] - d * 2.0)
        return out

    def stop(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][0]

    def target(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
