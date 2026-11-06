"""Independent check — manoj betrayed me (xeMt3ucD): 5-minute bars on an Asia/Kolkata chart (session 09:15-15:30, 24 h synthetic data), process_orders_on_close for market orders, pending stop entries. SMMA = RMA(20) of the high / low. buySignal = tradable bar with close > SMMA high; buyConfirm = buySignal on the previous bar and close > SMMA high and low > SMMA high now; the order is a buy-stop at the confirmation bar's high with its exit (stop = the previous bar's SMMA low, target = high + 2 x the bar's range); sell side mirrored. The pending entry is cancelled by the next bar's script if still unfilled (bar_index == pending + 1) and everything is cancelled outside the session; the bar whose close time is 15:30 or later cancels the pending orders and closes the position at its close. Uses the pending-order reference broker (simulate_ord, on_close). Margin off on the pinelib side. Variants: defaults; SMMA 10 with a 1.5 target multiple."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_rma, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "xeMt3ucD"


def one(df, params, ln, tm):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ist = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Asia/Kolkata")
    m = (ist.dt.hour * 60 + ist.dt.minute).to_numpy()
    ins = (m >= 555) & (m < 930)
    cl = ins & (m + 5 >= 930)
    can = ins & ~cl
    sh, sl = np_rma(h, ln), np_rma(l, ln)
    with np.errstate(invalid="ignore"):
        bs = can & (c > sh)
        ss = can & (c < sl)
    S = dict(pd=0, pb=-1)

    def orders(i, pos):
        out = []
        if cl[i]:
            out += [("cancel", "Buy"), ("cancel", "Sell"), ("close_all",)]
            S.update(pd=0, pb=-1)
        if not ins[i]:
            out += [("cancel", "Buy"), ("cancel", "Sell")]
            S.update(pd=0, pb=-1)
        if S["pd"] != 0 and i == S["pb"] + 1 and pos == 0:
            out.append(("cancel", "Buy" if S["pd"] == 1 else "Sell"))
            S.update(pd=0, pb=-1)
        if pos != 0:
            S.update(pd=0, pb=-1)
        nn = lambda v: None if np.isnan(v) else v
        with np.errstate(invalid="ignore"):
            bc = i > 0 and can[i] and bs[i - 1] and c[i] > sh[i] and l[i] > sh[i]
            sc = i > 0 and can[i] and ss[i - 1] and c[i] < sl[i] and h[i] < sl[i]
        if bc and pos == 0:
            out += [("cancel", "Sell"), ("entry", "Buy", 1, h[i], None), ("exit", "Buy Exit", "Buy", nn(sl[i - 1]), h[i] + tm * (h[i] - l[i]))]
            S.update(pd=1, pb=i)
        if sc and pos == 0:
            out += [("cancel", "Buy"), ("entry", "Sell", -1, l[i], None), ("exit", "Sell Exit", "Sell", nn(sh[i - 1]), l[i] - tm * (h[i] - l[i]))]
            S.update(pd=-1, pb=i)
        return out

    ref = simulate_ord(o, h, l, c, orders, on_close=True)
    sym = SymbolInfo.make("NSE:NIFTY", "stock", qty_step=1e-9, timezone="Asia/Kolkata", session="0915-1530")
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(40000, seed=212, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.4
    msgs, allok = [], True
    for params, args in (({}, (20, 2.0)), ({"SMMA Length": 10, "Target Multiplier": 1.5}, (10, 1.5))):
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
