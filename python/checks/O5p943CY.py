"""Independent check — 9 EMA (High/Low) (O5p943CY): 4-hour bars, one position, market orders at the next open, qty 1. Date range [2020-07-01, 2027-12-31) New York midnight. Inside it: close > EMA9(high) and not long -> (close the short,) enter long; close < EMA9(low) and not short -> (close the long,) enter short. Outside the range any position is closed. At every script run with a position, limit = avg x (1 +/- 0.62 %),
stop = avg x (1 -/+ 0.3 %) are (re)issued and work from the next bar (a reversed trade's first bracket is issued one bar after its fill). Variants: default, and 0.5 % target / 0.5 % stop. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "O5p943CY"


def one(df, params, tp_, sl_):
    o, h, l, c, t = (df[k].to_numpy() for k in ("open", "high", "low", "close", "time"))
    n = len(c)
    eh, el = np_ema(h, 9), np_ema(l, 9)
    t0 = pd.Timestamp(2020, 7, 1, tz="America/New_York").value // 10**6
    t1 = pd.Timestamp(2027, 12, 31, tz="America/New_York").value // 10**6
    inr = (t >= t0) & (t < t1)
    S = dict(ep=np.nan)
    poscl = np.zeros(n)
    tp_arr, sl_arr = np.full(n, np.nan), np.full(n, np.nan)
    with np.errstate(invalid="ignore"):
        buy, sell = c > eh, c < el

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if inr[i] and buy[i] and not pos > 0:
            if pos < 0:
                out.append(("close", -1))
            out.append(("entry", 1))
        if inr[i] and sell[i] and not pos < 0:
            if pos > 0:
                out.append(("close", 1))
            out.append(("entry", -1))
        if not inr[i] and pos != 0:
            out.append(("close", pos))
        if pos > 0:
            tp_arr[i], sl_arr[i] = S["ep"] * (1 + tp_ / 100), S["ep"] * (1 - sl_ / 100)
        if pos < 0:
            tp_arr[i], sl_arr[i] = S["ep"] * (1 - tp_ / 100), S["ep"] * (1 + sl_ / 100)
        return out

    def lvl(arr):
        def f(i, pos, ep, eb):
            S["ep"] = ep
            return None if (i == 0 or eb >= i or poscl[i - 1] * pos <= 0 or np.isnan(arr[i - 1])) else arr[i - 1]
        return f

    sf, tf = lvl(sl_arr), lvl(tp_arr)

    def stop(i, pos, ep, eb):
        S["ep"] = ep
        return sf(i, pos, ep, eb)

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tf)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="240", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(30000, seed=811, freq="4h")
    msgs, allok = [], True
    for params, a, b in (({}, 0.62, 0.3), ({"Target %": 0.5, "Stop-Loss %": 0.5}, 0.5, 0.5)):
        ok, m = one(df, params, a, b)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
