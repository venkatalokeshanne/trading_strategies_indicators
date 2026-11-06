"""Independent check — Traling.SL.Target (4jxYYaGU): daily bars, process_orders_on_close, one position (entries only while flat), trades closed at the close by condition. EMA20 crosses over / under EMA50 while flat -> long / short at the close with virtual target +/- 1 % and stop -/+ 1 % (fixed-point variant: 100 / 50 points); the reference entry
price starts at the close. On every bar (flat or not, on the stale levels once a trade is over): if the last trade side was long and close >= ref * 1.005 (or ref + 60 points) the reference, target and stop step up by 0.5 % / 0.3 % / 0.3 % (60 / 25 / 30 points); short: percent mode steps down when close <= ref * 0.995; fixed-point mode tests the original's `close >= ref - 60`.
A held long is closed at the close when close <= stop or close >= target; a held short when close >= stop or close <= target (conditions use the levels as updated on that bar). The close() calls see only trades open at script time. Variants: percent and fixed points. Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "4jxYYaGU"


def one(df, params, pct):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    f, s = np_ema(c, 20), np_ema(c, 50)
    gu, gd = np_cross_over(f, s), np_cross_under(f, s)
    S = dict(il=False, is_=False, lt=np.nan, ls=np.nan, st=np.nan, ss=np.nan, le=np.nan, se=np.nan)
    nan = np.nan

    def orders(i, pos):
        out = []
        glong, gshort = gu[i] and pos == 0, gd[i] and pos == 0
        if pct:
            ltp = c[i] >= S["le"] + S["le"] * 0.005
            stp = c[i] <= S["se"] - S["se"] * 0.005
        else:
            ltp = c[i] >= S["le"] + 60
            stp = c[i] >= S["se"] - 60
        if S["il"] and ltp:
            if pct:
                S["lt"] = S["lt"] + S["lt"] * 0.003
                S["ls"] = S["ls"] + S["ls"] * 0.003
                S["le"] = S["le"] + S["le"] * 0.005
            else:
                S["lt"] += 25
                S["ls"] += 30
                S["le"] += 60
        if S["is_"] and stp:
            if pct:
                S["st"] = S["st"] - S["st"] * 0.003
                S["ss"] = S["ss"] - S["ss"] * 0.003
                S["se"] = S["se"] - S["se"] * 0.005
            else:
                S["st"] -= 25
                S["ss"] -= 30
                S["se"] -= 60
        if glong:
            S["il"], S["is_"] = True, False
            S["le"] = c[i]
            S["lt"], S["ls"] = (c[i] + c[i] * 0.01, c[i] - c[i] * 0.01) if pct else (c[i] + 100, c[i] - 50)
            out.append(("entry", 1))
        if gshort:
            S["il"], S["is_"] = False, True
            S["se"] = c[i]
            S["st"], S["ss"] = (c[i] - c[i] * 0.01, c[i] + c[i] * 0.01) if pct else (c[i] - 100, c[i] + 50)
            out.append(("entry", -1))
        with np.errstate(invalid="ignore"):
            if pos > 0 and (c[i] <= S["ls"] or c[i] >= S["lt"]):
                out.append(("close", 1))
            if pos < 0 and (c[i] >= S["ss"] or c[i] <= S["st"]):
                out.append(("close", -1))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(14000, seed=891)
    msgs, allok = [], True
    for params, pct in (({}, True), ({"Method to be used for SL/Target trailing": "Fix point Based Target and SL"}, False)):
        ok, m = one(df, params, pct)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
