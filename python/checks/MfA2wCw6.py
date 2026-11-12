"""Independent check — CRT H3 Zonas Vela 0 + CHoCH (MfA2wCw6): 15-minute bars (24 h synthetic) of a stock-style symbol (New York time, 3-hour periods and trading days counted from 09:30), process_orders_on_close (orders fill at the signal close), default quantity 1, commission / slippage / margin off.
High / low of the running 3-hour period and of the previous one tracked on the chart bars (the first bar seeds both); 'looking for a sell' once the period high exceeds the previous period's high (buy for lows) while no entry was taken in the current New York day, both flags cleared at each new 3-hour period; change of character = close crossing under the last swing low [pivot left strictly lower / right not higher] (over the swing high for buys).
Entry with an exit order (stop at the running period extreme, limit at RR x risk), once per New York day (a sell does not set the day flag - the source quirk is kept). Uses the quantity-aware bracket reference (indep.simulate_brackets, on_close), comparing quantities too. Variants: defaults; swing length 2 with RR 2; swing length 5, RR 1.5."""
import numpy as np

from indep import bars, compare_q, np_periods, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "MfA2wCw6"


def pivots(x, k, high):
    n = len(x)
    out = np.full(n, np.nan)
    for i in range(2 * k, n):
        m = i - k
        c = x[m]
        lw, rw = x[m - k:m], x[m + 1:i + 1]
        ok = (np.all(c > lw) and np.all(c >= rw)) if high else (np.all(c < lw) and np.all(c <= rw))
        if ok:
            out[i] = c
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    dpid, _ = np_periods(df, 1440)
    hpid, _ = np_periods(df, 180)
    sh, sl = pivots(h, p["sw"], True), pivots(l, p["sw"], False)
    S = dict(eh=False, h0=np.nan, l0=np.nan, h1=np.nan, l1=np.nan, bv=False, bc=False, lsh=np.nan, lsl=np.nan)

    def orders(i, info):
        out = []
        if i > 0 and dpid[i] != dpid[i - 1]:
            S["eh"] = False
        nh = i > 0 and hpid[i] != hpid[i - 1]
        if np.isnan(S["h0"]):
            S["h0"], S["l0"] = h[i], l[i]
        if nh:
            S["h1"], S["l1"] = S["h0"], S["l0"]
            S["h0"], S["l0"] = h[i], l[i]
        else:
            S["h0"], S["l0"] = max(S["h0"], h[i]), min(S["l0"], l[i])
        if not np.isnan(sh[i]):
            S["lsh"] = sh[i]
        if not np.isnan(sl[i]):
            S["lsl"] = sl[i]
        with np.errstate(invalid="ignore"):
            th = not np.isnan(S["h1"]) and S["h0"] > S["h1"]
            tl = not np.isnan(S["l1"]) and S["l0"] < S["l1"]
            if nh:
                S["bv"] = S["bc"] = False
            if not S["eh"] and th:
                S["bv"], S["bc"] = True, False
            if not S["eh"] and tl:
                S["bc"], S["bv"] = True, False
            ca = not np.isnan(S["lsh"]) and c[i] > S["lsh"] and i > 0 and c[i - 1] <= S["lsh"]
            cb = not np.isnan(S["lsl"]) and c[i] < S["lsl"] and i > 0 and c[i - 1] >= S["lsl"]
            compra = (not S["eh"]) and S["bc"] and ca and info["pos"] == 0
            venta = (not S["eh"]) and S["bv"] and cb and info["pos"] == 0
            rc, rv = c[i] - S["l0"], S["h0"] - c[i]
        if compra and rc > 0:
            out += [("entry", "BUY CRT", 1, 1.0), ("exit", "TP/SL BUY", "BUY CRT", None, S["l0"], c[i] + rc * p["rr"])]
            S["bc"] = False
            S["eh"] = True
        if venta and rv > 0:
            out += [("entry", "SELL CRT", -1, 1.0), ("exit", "TP/SL SELL", "SELL CRT", None, S["h0"], c[i] - rv * p["rr"])]
            S["bv"] = False
        return out

    ref = simulate_brackets(o, h, l, c, orders, on_close=True)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(sw=3, rr=1.0)


def check():
    df = bars(60000, seed=491, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    cases = (({}, {}), ({"Fuerza del Swing / CHoCH": 2, "Risk Reward": 2.0}, dict(sw=2, rr=2.0)), ({"Fuerza del Swing / CHoCH": 5, "Risk Reward": 1.5}, dict(sw=5, rr=1.5)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
