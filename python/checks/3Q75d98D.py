"""Independent check — Simple ZigZag Double (3Q75d98D): daily bars, 100 % equity, pending stop entries (the quantity does not change the trade list). Turning points of a triple-smoothed EMA (lengths round(L), round(2L/3), round(L/3) chained, each on the previous) mark swings: an up-turn (EMA rises after having fallen) takes the lowest low of the detection window, a down-turn the highest high; the "point" is the last swing price. LEVEL_LONG = the swing price when the long detector's point rose, LEVEL_SHORT2 = the swing price when the short detector's point fell (each held until the next such event). A buy-stop at LEVEL_LONG and a sell-stop at LEVEL_SHORT2 are renewed every bar when positive. With one direction disabled the other detector's level becomes the exit stop of the open trade and the disabled side's pending entry is cancelled; "strict position" tracks a virtual position that must be re-armed by a fresh breakout; everything closes after the end time. Uses the pending-order reference broker (simulate_ord). Commission / margin off on the pinelib side.
Variants: defaults; shorts off (exit stop at LEVEL_SHORT2 of the short detector); different lengths with strict position; an end time inside the data."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion, simulate_ord

TV_ID = "3Q75d98D"


def ema_na(x, n):
    out = np.full(len(x), np.nan)
    idx = np.flatnonzero(~np.isnan(x))
    if len(idx) < n:
        return out
    s = idx[0] + n - 1
    out[s] = x[idx[0]:s + 1].mean()
    k = 2.0 / (n + 1)
    for i in range(s + 1, len(x)):
        out[i] = k * x[i] + (1 - k) * out[i - 1]
    return out


def rnd(x):
    return int(np.floor(x + 0.5))


def swing(c, l, h, length, det):
    n = len(c)
    e1 = ema_na(c, rnd(length / 3 * 3))
    e2 = ema_na(e1, rnd(length / 3 * 2))
    e3 = ema_na(e2, rnd(length / 3))
    lo = np.array([l[i - det + 1:i + 1].min() if i >= det - 1 else np.nan for i in range(n)])
    hi = np.array([h[i - det + 1:i + 1].max() if i >= det - 1 else np.nan for i in range(n)])
    z = np.zeros(n)
    point = np.full(n, np.nan)
    llong, lshort = np.full(n, np.nan), np.full(n, np.nan)
    with np.errstate(invalid="ignore"):
        for i in range(n):
            a1 = e3[i - 1] if i >= 1 else np.nan
            a2 = e3[i - 2] if i >= 2 else np.nan
            if e3[i] >= a1 and a1 < a2:
                z[i] = lo[i]
            elif e3[i] < a1 and a1 >= a2:
                z[i] = hi[i]
            else:
                z[i] = 0.0
            p1 = point[i - 1] if i else np.nan
            point[i] = p1 if z[i] == 0.0 else z[i]
            llong[i] = z[i] if point[i] > p1 else (llong[i - 1] if i else np.nan)
            lshort[i] = z[i] if point[i] < p1 else (lshort[i - 1] if i else np.nan)
    return llong, lshort


def one(df, params, needlong, needshort, L1, D1, L2, D2, strict, tend):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    t = df["time"].to_numpy()
    LL, _ = swing(c, l, h, L1, D1)
    _, LS2 = swing(c, l, h, L2, D2)
    S = dict(vp=0)

    def orders(i, pos):
        out = []
        tt = t[i] > 1388534400000 and t[i] < tend
        if strict:
            with np.errstate(invalid="ignore"):
                if S["vp"] == 1 and c[i] <= LS2[i] and c[i - 1] > LS2[i]:
                    S["vp"] = 0
                if S["vp"] == -1 and c[i] >= LL[i] and c[i - 1] < LL[i]:
                    S["vp"] = 0
                if S["vp"] != 1 and c[i] >= LL[i]:
                    S["vp"] = 1
                if S["vp"] != -1 and c[i] <= LS2[i]:
                    S["vp"] = -1
        nn = lambda v: None if np.isnan(v) else v
        if LL[i] > 0 and needlong and tt and S["vp"] != 1:
            out.append(("entry", "Long", 1, LL[i], None))
        if LS2[i] > 0 and needshort and tt and S["vp"] != -1:
            out.append(("entry", "Short", -1, LS2[i], None))
        if not needlong:
            out.append(("cancel", "Long"))
        if not needshort:
            out.append(("exit", "Exit Long", "Long", nn(LS2[i]), None))
            out.append(("cancel", "Short"))
        if not needlong:
            out.append(("exit", "Exit Short", "Short", nn(LL[i]), None))
        if t[i] > tend:
            out += [("close_all",), ("cancel", "Long"), ("cancel", "Short")]
            S["vp"] = 0
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate_ord(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, params=params, strategy_overrides={"commission_value": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(3000, seed=58)
    end_mid = int(df["time"].iloc[2000])
    msgs, allok = [], True
    cases = (({}, (True, True, 5, 3, 5, 3, False, 2556057540000)),
             ({"Use Short": False}, (True, False, 5, 3, 5, 3, False, 2556057540000)),
             ({"Long Length": 8, "Short Length": 6, "Strict position": True}, (True, True, 8, 3, 6, 3, True, 2556057540000)),
             ({"Time End  ": end_mid}, (True, True, 5, 3, 5, 3, False, end_mid)))
    for params, args in cases:
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
