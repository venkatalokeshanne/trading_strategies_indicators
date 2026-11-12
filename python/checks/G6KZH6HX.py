"""Independent check — Trend Pullback Re-Entry (G6KZH6HX): daily bars, one position, trade list only. Uptrend = EMA55 > EMA233 and EMA233 > its value 10 bars ago (downtrend mirrored). Short RSI5 dip: barssince(RSI5 <= 25) <= 3 (na = 100000 = never); pop: barssince(RSI5 >= 75) <= 3.
Long: warm (bar index > 243), flat, uptrend, recent dip, close > previous high (short: downtrend, recent pop, close < previous low). Initial stop = lowest low of the last 4 bars - 0.5 ATR14 (unit = max(ATR, 0.01), na ATR -> bar range) placed with the entry (works from the
fill bar). While in a position at a script run the trail = max(trail, close - 5 unit) (short: min(trail, close + 5 unit)) and is re-issued, so bar i works with bar i-1's trail. Margin and slippage off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "G6KZH6HX"


def since(cond):
    out = np.full(len(cond), 100000.0)
    last = None
    for i, x in enumerate(cond):
        if x:
            last = i
        if last is not None:
            out[i] = i - last
    return out


def check():
    df = bars(8000, seed=285)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ef, es = np_ema(c, 55), np_ema(c, 233)
    es10 = np.r_[np.full(10, np.nan), es[:-10]]
    rsi5 = np_rsi(c, 5)
    atr = np_atr(h, l, c, 14)
    unit = np.maximum(np.where(np.isnan(atr), h - l, atr), 0.01)
    with np.errstate(invalid="ignore"):
        up, dn = (ef > es) & (es > es10), (ef < es) & (es < es10)
        sd, sp = since(rsi5 <= 25.0), since(rsi5 >= 75.0)
    dip = pd.Series(l).rolling(4, min_periods=4).min().to_numpy()
    pop = pd.Series(h).rolling(4, min_periods=4).max().to_numpy()
    h1, l1 = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    S = dict(trail=np.nan)
    poscl = np.zeros(n)
    tr_arr = np.full(n, np.nan)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        warm = i > 233 + 10
        with np.errstate(invalid="ignore"):
            ls = warm and pos == 0 and up[i] and sd[i] <= 3 and c[i] > h1[i]
            ss = warm and pos == 0 and dn[i] and sp[i] <= 3 and c[i] < l1[i]
        if ls:
            stop = dip[i] - 0.5 * unit[i]
            if c[i] - stop > 0:
                S["trail"] = stop
                out.append(("entry", 1))
                tr_arr[i] = stop
        elif ss:
            stop = pop[i] + 0.5 * unit[i]
            if stop - c[i] > 0:
                S["trail"] = stop
                out.append(("entry", -1))
                tr_arr[i] = stop
        elif pos > 0:
            S["trail"] = max(c[i] - 5.0 * unit[i] if np.isnan(S["trail"]) else S["trail"], c[i] - 5.0 * unit[i])
            tr_arr[i] = S["trail"]
        elif pos < 0:
            S["trail"] = min(c[i] + 5.0 * unit[i] if np.isnan(S["trail"]) else S["trail"], c[i] + 5.0 * unit[i])
            tr_arr[i] = S["trail"]
        else:
            S["trail"] = np.nan
        return out

    def stop(i, pos, ep, eb):
        if i == 0 or np.isnan(tr_arr[i - 1]):
            return None
        return tr_arr[i - 1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
