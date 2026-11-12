"""Independent check — ATR Breakout Trend (ANmKXWWJ): daily bars, process_orders_on_close, one position (entries reverse), trade list only. Entry channel = previous 20 bars' highest high / lowest low; long when the close crosses over it with close > SMA200, short when it
crosses under with close < SMA200; ATR = SMA20 of the true range; entries at the close with the stop = close -/+ 2 ATR placed together. While in a position at a script run the same stop is re-issued (works from the next bar) and a close below the previous 20 bars' lowest
low (above the highest high for shorts) closes the trade at the close instead. Variants: default and the ATR trailing stop (stop = max(stop, high - 2 ATR) / min(stop, low + 2 ATR)). Margin and slippage off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_sma, np_tr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "ANmKXWWJ"


def one(df, trail):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sh = lambda x: np.r_[np.nan, x[:-1]]
    eh = sh(pd.Series(h).rolling(20, min_periods=20).max().to_numpy())
    el = sh(pd.Series(l).rolling(20, min_periods=20).min().to_numpy())
    atr = np_sma(np_tr(h, l, c, True), 20)
    sma = np_sma(c, 200)
    with np.errstate(invalid="ignore"):
        lb = np_cross_over(c, eh) & (c > sma)
        sb = np_cross_under(c, el) & (c < sma)
    S = dict(ls=np.nan, ss=np.nan)
    poscl = np.zeros(n)
    stop_arr = np.full(n, np.nan)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        ok = atr[i] > 0
        if lb[i] and pos <= 0 and ok:
            S["ls"], S["ss"] = c[i] - 2.0 * atr[i], np.nan
            out.append(("entry", 1))
            stop_arr[i] = S["ls"]
        if sb[i] and pos >= 0 and ok:
            S["ss"], S["ls"] = c[i] + 2.0 * atr[i], np.nan
            out.append(("entry", -1))
            stop_arr[i] = S["ss"]
        if pos > 0 and not np.isnan(S["ls"]):
            if trail:
                S["ls"] = max(S["ls"], h[i] - 2.0 * atr[i])
            if c[i] < el_exit[i]:
                out.append(("close", 1))
            else:
                stop_arr[i] = S["ls"]
        if pos < 0 and not np.isnan(S["ss"]):
            if trail:
                S["ss"] = min(S["ss"], l[i] + 2.0 * atr[i])
            if c[i] > eh_exit[i]:
                out.append(("close", -1))
            else:
                stop_arr[i] = S["ss"]
        return out

    eh_exit, el_exit = eh, el          # exit channel length equals the entry length (20)

    def stop(i, pos, ep, eb):
        if i == 0 or np.isnan(stop_arr[i - 1]):
            return None
        return stop_arr[i - 1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    params = {"Enable ATR trailing stop": True} if trail else {}
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"trail={trail}: {d} (got {len(ref)})"


def check():
    df = bars(7000, seed=326)
    msgs, allok = [], True
    for tr in (False, True):
        ok, m = one(df, tr)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
