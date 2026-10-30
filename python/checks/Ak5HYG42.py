"""Independent check — Ultimate SMC + EMAs Day Trading Strategy (Ak5HYG42): 15-minute bars (24 h synthetic, price ~100) of a stock-style symbol, 1 contract per entry, market orders at the next open, commission / slippage off.
10-bar pivots, the fib range from the high / low 5 bars before the latest pivot detections (valuewhen), its 0.618 level, the EMA 9/21 and SMA 200 trend, the three-bar fair-value gaps and the 9-EMA cross, the 4-hour high / low frozen as target / stop at entry (lookahead off) and the exit orders re-issued every bar are restated bar by bar.
Uses the quantity-aware bracket reference (indep.simulate_brackets). Variants: defaults; pivot length 6 with EMA 5/13."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_cross_over, np_cross_under, np_ema, np_periods, np_security_lookahead_off, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "Ak5HYG42"


def pivots(x, left, right, high):
    out = np.full(len(x), False)
    for i in range(left + right, len(x)):
        w = x[i - left - right:i + 1]
        ctr = w[left]
        a, b = w[:left], w[left + 1:]
        out[i] = ((a < ctr).all() and (b <= ctr).all()) if high else ((a > ctr).all() and (b >= ctr).all())
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    e9, e21, s200 = np_ema(c, p["e1"]), np_ema(c, p["e2"]), np_sma(c, 200)
    pid, last_of = np_periods(df, 240)
    g = pd.DataFrame({"pid": pid, "h": h, "l": l}).groupby("pid")
    hth = np_security_lookahead_off(g["h"].max().to_numpy(), pid, last_of)
    htl = np_security_lookahead_off(g["l"].min().to_numpy(), pid, last_of)
    up, dn = pivots(h, p["tl"], p["tl"], True), pivots(l, p["tl"], p["tl"], False)
    xu, xd = np_cross_over(c, e9), np_cross_under(c, e9)
    S = dict(top=np.nan, bot=np.nan, f618=np.nan, sl=np.nan, tp=np.nan)

    def orders(i, info):
        out = []
        pos = info["pos"]
        h2, l2, c1 = (h[i - 2], l[i - 2], c[i - 1]) if i >= 2 else (np.nan,) * 3
        with np.errstate(invalid="ignore"):
            bull = l[i] > h2 and c1 > h2
            bear = h[i] < l2 and c1 < l2
            if up[i]:
                S["top"] = h[i - 5] if i >= 5 else np.nan
            if dn[i]:
                S["bot"] = l[i - 5] if i >= 5 else np.nan
            if up[i] or dn[i]:
                S["f618"] = S["bot"] + (S["top"] - S["bot"]) * 0.618
            bt, br = c[i] > s200[i] and e9[i] > e21[i], c[i] < s200[i] and e9[i] < e21[i]
            lc = bool(bt and (c[i] <= S["f618"] or l[i] <= S["bot"]) and (bull or xu[i]))
            sc = bool(br and (c[i] >= S["f618"] or h[i] >= S["top"]) and (bear or xd[i]))
        nn = lambda x: None if np.isnan(x) else float(x)
        if lc and pos == 0:
            S["sl"], S["tp"] = htl[i], hth[i]
            out.append(("entry", "Long", 1, 1.0))
        if sc and pos == 0:
            S["sl"], S["tp"] = hth[i], htl[i]
            out.append(("entry", "Short", -1, 1.0))
        if pos > 0:
            out.append(("exit", "Exit Long", "Long", None, nn(S["sl"]), nn(S["tp"])))
        if pos < 0:
            out.append(("exit", "Exit Short", "Short", None, nn(S["sl"]), nn(S["tp"])))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=0.01, qty_step=1e-9)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


def check():
    df = bars(40000, seed=5, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    cases = (({}, dict(e1=9, e2=21, tl=10)),
             ({"Trendline Pivot Length": 6, "EMA 9 Length": 5, "EMA 21 Length": 13}, dict(e1=5, e2=13, tl=6)))
    for params, ov in cases:
        ok, m = one(df, params, ov)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
