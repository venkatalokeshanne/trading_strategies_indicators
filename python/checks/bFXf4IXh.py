"""Independent check — Built-in Kelly ratio (bFXf4IXh): daily bars, pending stop-entry orders (the sizing does not change the trade list, only the quantity). Bands: moving average (EMA or SMA, 20) +/- multiplier x (ATR(10) | RMA of the true range | RMA of the range). A close crossing above the upper band leaves a pending buy-stop at that bar's high + 1 tick (cross below the lower band: sell-stop at low - 1 tick); the "crossed" flag is sticky from the first cross on, and from then on the pending order of that side is cancelled at every bar whose close is back under the average (over for shorts) or whose high reaches the stop price (low for shorts) - before a new entry of the same bar is issued. Pending stops fill at their level (at the open when gapped), opposite ones reverse. Optional take-profit / stop-loss exits are in points from the average price (percent of it), issued every bar (an exit call whose every level is na - the average price is na while flat - replaces, i.e. removes, the previous exit of that id). Commission and margin off on the pinelib side.
Variants: ATR bands with EMA; True-Range bands with SMA and a 5 % target; Range bands, 2 % stop and a 6 % target, no Kelly sizing."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_rma, np_sma, np_tr, run_conversion, simulate_ord

TV_ID = "bFXf4IXh"


def one(df, params, style, use_exp, mult, tp, sl):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ma = np_ema(c, 20) if use_exp else np_sma(c, 20)
    if style == "atr":
        rg = np_atr(h, l, c, 10)
    elif style == "tr":
        rg = np_rma(np_tr(h, l, c, handle_na=True), 20)
    else:
        rg = np_rma(h - l, 20)
    up, lo = ma + rg * mult, ma - rg * mult
    pc, pu, pl = np.r_[np.nan, c[:-1]], np.r_[np.nan, up[:-1]], np.r_[np.nan, lo[:-1]]
    with np.errstate(invalid="ignore"):
        cu = (c > up) & (pc <= pu)
        cl = (c < lo) & (pc >= pl)
    S = dict(bp=0.0, sp=0.0, cb=False, cs=False)

    def orders(i, pos, info):
        out = []
        if cu[i]:
            S["bp"] = h[i] + 0.01
        if cl[i]:
            S["sp"] = l[i] - 0.01
        S["cb"] = S["cb"] or bool(cu[i])
        S["cs"] = S["cs"] or bool(cl[i])
        cancel_b = S["cb"] and (c[i] < ma[i] or h[i] >= S["bp"])
        cancel_s = S["cs"] and (c[i] > ma[i] or l[i] <= S["sp"])
        if cancel_b:
            out.append(("cancel", "Long"))
        if cu[i]:
            out.append(("entry", "Long", 1, S["bp"], None))
        if cancel_s:
            out.append(("cancel", "Short"))
        if cl[i]:
            out.append(("entry", "Short", -1, S["sp"], None))
        if tp or sl:       # issued at every bar; with the average price na (flat) every level is na and the call replaces (= removes) the id's previous exit
            avg = info["ep"] if pos != 0 else None
            prof = avg * tp / 100 if (tp and avg is not None) else None
            loss = avg * sl / 100 if (sl and avg is not None) else None
            out.append(("exit", "Long Exit", "Long", None, None, prof, loss))
            out.append(("exit", "Short Exit", "Short", None, None, prof, loss))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate_ord(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, params=params, strategy_overrides={"commission_value": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(5000, seed=303)
    msgs, allok = [], True
    cases = (({}, ("atr", True, 1.0, 0, 0)),
             ({"Bands Style": "True Range", "Use Exponential MA": False, "use Take Profit": True, "take profit": 5.0}, ("tr", False, 1.0, 5.0, 0)),
             ({"Bands Style": "Range", "use Take Profit": True, "use Stop Loss": True, "take profit": 6.0, "stop loss": 2.0, "Kelly Ratio Position Sizing": False, "Multiplier": 0.8},
              ("rng", True, 0.8, 6.0, 2.0)))
    for params, args in cases:
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
