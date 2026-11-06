"""Independent check — Lucky13ema Filtered v2 (ii4VZhUA): 5-min New York bars. Green candle closing above EMA13 after a close at/below it, with volume > 1.2 x SMA20 and
the close on the right side of the session VWAP(hlc3) (filters on), enters (reversing; shorts mirrored). Exits unconditional: trailing stop with activation 10 ticks
and offset 10 ticks (mintick 0.01) from the entry price, pending before the fill so already working on the fill bar. The second run turns trailing off: profit 2 ticks
/ loss 1 tick (0.02 / 0.01). Margin off on the pinelib side (100 % of equity, v5 default is margin 0 anyway)."""
import numpy as np

from indep import bars, compare, np_ema, np_sma, np_vwap, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "ii4VZhUA"


def one(seed, trailing):
    df = bars(20000, seed=seed, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    e = np_ema(c, 13)
    pe, pc = np.r_[np.nan, e[:-1]], np.r_[np.nan, c[:-1]]
    vw = np_vwap(df, (h + l + c) / 3)
    vol_ok = v > np_sma(v, 20) * 1.2
    with np.errstate(invalid="ignore"):
        buy = (c > o) & (c > e) & (pc <= pe) & vol_ok & (c > vw)
        sell = (c < o) & (c < e) & (pc >= pe) & vol_ok & (c < vw)
    orders = lambda i, pos: ([("entry", 1)] if buy[i] and pos <= 0 else []) + ([("entry", -1)] if sell[i] and pos >= 0 else [])
    if trailing:
        ref = simulate(o, h, l, c, orders, trail=lambda i, pos, ep, eb: (10.0, 10.0), tick=0.01)
    else:
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: ep - pos * 0.01, target=lambda i, pos, ep, eb: ep + pos * 0.02)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    params = {} if trailing else {"Use Trailing Stop": False}
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok, detail, len(ref)


def check():
    res = [one(162, True), one(163, False)]
    bad = [r[1] for r in res if not r[0]]
    total = sum(r[2] for r in res)
    return (not bad) and total > 10, (bad[0] if bad else f"{res[0][2]} trailing + {res[1][2]} fixed trades identical") + f" (need >10 trades, got {total})"
