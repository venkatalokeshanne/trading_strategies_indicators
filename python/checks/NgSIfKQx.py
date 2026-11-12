"""Independent check — Bitcoin SuperFlip (NgSIfKQx): hourly bars, one position, trade list only. SuperTrend(1.8, ATR10) flips: to up (direction -1) with close > EMA200 goes long; to down with close < EMA200 goes short; every flip also closes the opposite
side after the entry orders (ignored when already reversed). Variants: defaults; stop 1.5% / target 3% enabled (placed around the entry price while in a position, so bar i works with bar i-1's levels if a same-side position existed at bar i-1's script run).
Margin and slippage off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_ema, np_supertrend, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "NgSIfKQx"


def one(df, sltp):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    _, d = np_supertrend(h, l, c, 1.8, 10)
    chg = d - np.r_[np.nan, d[:-1]]
    ema = np_ema(c, 200)
    with np.errstate(invalid="ignore"):
        bf, rf = chg < 0, chg > 0
        ls = bf & (c > ema)
        ss = rf & (c < ema)
    poscl = np.zeros(n)
    ep_now = {"i": -1, "ep": np.nan}
    avg_at = np.full(n, np.nan)

    def orders(i, pos):
        poscl[i] = pos
        if pos != 0 and ep_now["i"] == i:
            avg_at[i] = ep_now["ep"]
        out = []
        if ls[i]:
            out.append(("entry", 1))
        if ss[i]:
            out.append(("entry", -1))
        if rf[i]:
            out.append(("close", 1))
        if bf[i]:
            out.append(("close", -1))
        return out

    def stop(i, pos, ep, eb):
        ep_now["i"], ep_now["ep"] = i, ep
        if not sltp or i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(avg_at[i - 1]):
            return None
        return avg_at[i - 1] * (1 - 0.015 * pos)

    def target(i, pos, ep, eb):
        if not sltp or i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(avg_at[i - 1]):
            return None
        return avg_at[i - 1] * (1 + 0.03 * pos)

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    params = {"Enable Stop Loss": True, "Enable Take Profit": True, "Stop Loss %": 1.5, "Take Profit %": 3.0} if sltp else {}
    ok, dd = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"sltp={sltp}: {dd} (got {len(ref)})"


def check():
    df = bars(15000, seed=833, freq="1h")
    msgs, allok = [], True
    for s in (False, True):
        ok, m = one(df, s)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
