"""Independent check — Liquidity Sweep Rider (Wys8loiZ): daily bars, one position (reversals), trade list only. Swing pivots 5 left (strict) / 5 right (non-strict); the latest confirmed swing low / high are the liquidity levels.
Bull sweep: low < level, close > level and volume >= 2.0 x SMA20(volume) (volume multiplier loosened to 1.0 on both sides so signals occur); entry gated by 20 bars since the last bull (bear) sweep entry. While in a position at a
script run the stop / target are 1.2 / 3.0 ATR14 around the position average price, so bar i works with bar i-1's ATR and the entry price, only if a same-side position existed at bar i-1's script run. Margin, slippage off."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "Wys8loiZ"


def pivots(x, L, R, high):
    n = len(x)
    out = np.full(n, np.nan)
    for i in range(L + R, n):
        p = i - R
        left, right = x[p - L:p], x[p + 1:p + R + 1]
        if high:
            if all(x[p] > left) and all(x[p] >= right):
                out[i] = x[p]
        else:
            if all(x[p] < left) and all(x[p] <= right):
                out[i] = x[p]
    return out


def check():
    df = bars(7000, seed=644)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    buy_liq = pd.Series(pivots(l, 5, 5, False)).ffill().to_numpy()
    sell_liq = pd.Series(pivots(h, 5, 5, True)).ffill().to_numpy()
    av = np_sma(v, 20)
    atr = np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        bs = (l < buy_liq) & (c > buy_liq) & (v >= av * 1.0)
        es = (h > sell_liq) & (c < sell_liq) & (v >= av * 1.0)
    S = dict(lb=-999, le=-999)
    poscl = np.zeros(n)
    ep_now = {"i": -1, "ep": np.nan}
    avg_at = np.full(n, np.nan)

    def orders(i, pos):
        poscl[i] = pos
        if pos != 0 and ep_now["i"] == i:
            avg_at[i] = ep_now["ep"]
        out = []
        if bs[i] and (i - S["lb"] > 20):
            out.append(("entry", 1))
            S["lb"] = i
        if es[i] and (i - S["le"] > 20):
            out.append(("entry", -1))
            S["le"] = i
        return out

    def stop(i, pos, ep, eb):
        ep_now["i"], ep_now["ep"] = i, ep
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(avg_at[i - 1]):
            return None
        return avg_at[i - 1] - pos * atr[i - 1] * 1.2

    def target(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(avg_at[i - 1]):
            return None
        return avg_at[i - 1] + pos * atr[i - 1] * 1.2 * 2.5

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"HFT Huge Volume Multiplier (Institutional Grabber Filter)": 1.0},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "default_qty_value": 5}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
