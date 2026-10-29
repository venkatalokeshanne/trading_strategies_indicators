"""Independent check — Auto-Logger Signal Tracker (7VqlwJsL): daily bars, one position, 1 unit. With the default inputs nothing trades (asserted: zero trades). With the "Trend Signals Long" and "Sniper Entry Short" inputs on, a long is entered
at every bar close while flat (stop = low x 0.99, target = close + 19 x (close - stop), fixed at the signal and working from the fill bar) and a short likewise (stop = high x 1.01, target = close - 19 x (stop - close)). With both on, the long is evaluated first and the short test still sees a flat position, so both entry orders are issued and the later one wins as a reversal at the next open. Margin and slippage off on the pinelib side."""
import numpy as np

from indep import bars, compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "7VqlwJsL"
RR = 19.0


def one(df, params, long_on, short_on):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    lv = {1: None, -1: None}

    def orders(i, pos):
        out = []
        if long_on and pos == 0:
            sl = l[i] * 0.99
            lv[1] = (sl, c[i] + (c[i] - sl) * RR)
            out.append(("entry", 1))
        if short_on and pos == 0:
            sl = h[i] * 1.01
            lv[-1] = (sl, c[i] - (sl - c[i]) * RR)
            out.append(("entry", -1))
        return out

    def stop(i, pos, ep, eb):
        return lv[pos][0] if lv[pos] else None

    def target(i, pos, ep, eb):
        return lv[pos][1] if lv[pos] else None

    ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "default_qty_value": 1}), ref)
    return ok, f"{params or 'defaults'}: {d}", len(ref)


def check():
    df = bars(3000, seed=818)
    msgs, allok = [], True
    ok, m, n0 = one(df, {}, False, False)
    allok &= ok and n0 == 0
    msgs.append(m)
    ok, m, n1 = one(df, {"Trend Signals [UAlgo] Long": True}, True, False)
    allok &= ok and n1 > 5
    msgs.append(m)
    ok, m, n2 = one(df, {"Sniper Entry [KhanSaab] Short": True}, False, True)
    allok &= ok and n2 > 5
    msgs.append(m)
    ok, m, n3 = one(df, {"Trend Signals [UAlgo] Long": True, "Sniper Entry [KhanSaab] Short": True}, True, True)
    allok &= ok and n3 > 5
    msgs.append(m)
    return allok, " | ".join(msgs)
