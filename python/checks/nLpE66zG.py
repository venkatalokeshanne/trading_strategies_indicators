"""Independent check — XAUUSD Wyckoff Second Breakout V3 (nLpE66zG): 15-minute bars of a stock-style symbol (price ~100), market orders at the next open, default quantity 1, pyramiding 0, commission / slippage / margin off.
Per side a staged state machine (long: 0 -> first close over the last pivot high [pivot: left strictly lower, right not higher] -> stage 1 (running high / pull-back low, bar counter; the close under the running high advances to stage 2 on the same bar, the counter above the wait limit resets) -> stage 2 (counter and pull-back low continue; a close over the running high while flat enters
with the stop under the pull-back low minus ATR x buffer and a limit at the risk multiple chosen by trend expansion / low liquidity / normal; the stage then resets)), restated statement by statement, shorts mirrored. Entry and exit order are issued together. Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too.
Variants: defaults with a short wait limit 10 and pivots 3 / 2; shorts disabled with an RR table 0.8 / 1.5 / 2.5."""
import numpy as np

from indep import bars, compare_q, np_atr, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "nLpE66zG"


def pivots(x, left, right, high):
    n = len(x)
    out = np.full(n, np.nan)
    for i in range(left + right, n):
        m = i - right
        c = x[m]
        lw, rw = x[m - left:m], x[m + 1:i + 1]
        ok = (np.all(c > lw) and np.all(c >= rw)) if high else (np.all(c < lw) and np.all(c <= rw))
        if ok:
            out[i] = c
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr = np_atr(h, l, c, 14)
    body, rng = np.abs(c - o), h - l
    ab, ar = np_sma(body, 50), np_sma(rng, 100)
    rb, rr_ = np_sma(body, 10), np_sma(rng, 10)
    ph, pl = pivots(h, p["lb"], p["rb"], True), pivots(l, p["lb"], p["rb"], False)
    S = dict(lph=np.nan, lpl=np.nan, ls=0, lh2=np.nan, lpb=np.nan, lb=0, ss=0, sl2=np.nan, sbh=np.nan, sb=0)
    W = p["wait"]

    def orders(i, info):
        out = []
        pos = info["pos"]
        if not np.isnan(ph[i]):
            S["lph"] = ph[i]
        if not np.isnan(pl[i]):
            S["lpl"] = pl[i]
        with np.errstate(invalid="ignore"):
            lowliq = rb[i] < ab[i] * 0.75 and rr_[i] < ar[i] * 0.75
            lsc = c[i] >= h[i] - rng[i] * 0.30 if rng[i] > 0 else False
            ssc = c[i] <= l[i] + rng[i] * 0.30 if rng[i] > 0 else False
            lte = c[i] > o[i] and body[i] > ab[i] * 1.5 and rng[i] > atr[i] * 1.0 and lsc
            ste = c[i] < o[i] and body[i] > ab[i] * 1.5 and rng[i] > atr[i] * 1.0 and ssc
            # ---- long
            if p["ul"] and S["ls"] == 0 and not np.isnan(S["lph"]) and c[i] > S["lph"]:
                S.update(ls=1, lh2=h[i], lpb=l[i], lb=0)
            if S["ls"] == 1:
                S["lb"] += 1
                S["lh2"], S["lpb"] = max(S["lh2"], h[i]), min(S["lpb"], l[i])
                if c[i] < S["lh2"]:
                    S["ls"] = 2
                if S["lb"] > W:
                    S.update(ls=0, lh2=np.nan, lpb=np.nan)
            if S["ls"] == 2:
                S["lb"] += 1
                S["lpb"] = min(S["lpb"], l[i])
            if p["ul"] and S["ls"] == 2 and c[i] > S["lh2"] and pos == 0:
                stop = S["lpb"] - 0.2 * atr[i]
                risk = c[i] - stop
                rr = p["rrt"] if lte else (p["rrl"] if lowliq else p["rrn"])
                if risk > 0:
                    out += [("entry", "Long", 1, 1.0), ("exit", "Long Exit", "Long", None, stop, c[i] + rr * risk)]
                S.update(ls=0, lh2=np.nan, lpb=np.nan)
            if S["ls"] == 2 and S["lb"] > W:
                S.update(ls=0, lh2=np.nan, lpb=np.nan)
            # ---- short
            if p["us"] and S["ss"] == 0 and not np.isnan(S["lpl"]) and c[i] < S["lpl"]:
                S.update(ss=1, sl2=l[i], sbh=h[i], sb=0)
            if S["ss"] == 1:
                S["sb"] += 1
                S["sl2"], S["sbh"] = min(S["sl2"], l[i]), max(S["sbh"], h[i])
                if c[i] > S["sl2"]:
                    S["ss"] = 2
                if S["sb"] > W:
                    S.update(ss=0, sl2=np.nan, sbh=np.nan)
            if S["ss"] == 2:
                S["sb"] += 1
                S["sbh"] = max(S["sbh"], h[i])
            if p["us"] and S["ss"] == 2 and c[i] < S["sl2"] and pos == 0:
                stop = S["sbh"] + 0.2 * atr[i]
                risk = stop - c[i]
                rr = p["rrt"] if ste else (p["rrl"] if lowliq else p["rrn"])
                if risk > 0:
                    out += [("entry", "Short", -1, 1.0), ("exit", "Short Exit", "Short", None, stop, c[i] - rr * risk)]
                S.update(ss=0, sl2=np.nan, sbh=np.nan)
            if S["ss"] == 2 and S["sb"] > W:
                S.update(ss=0, sl2=np.nan, sbh=np.nan)
        return out

    ref = simulate_brackets(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(lb=4, rb=2, wait=20, ul=True, us=True, rrl=1.0, rrn=2.0, rrt=3.0)


def check():
    df = bars(30000, seed=451, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Max Bars After First Breakout": 10, "Pivot Left Bars": 3, "Pivot Right Bars": 2}, dict(wait=10, lb=3, rb=2)),
             ({"Enable Short": False, "RR Low Liquidity": 0.8, "RR Normal": 1.5, "RR Trend Expansion": 2.5}, dict(us=False, rrl=0.8, rrn=1.5, rrt=2.5)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
