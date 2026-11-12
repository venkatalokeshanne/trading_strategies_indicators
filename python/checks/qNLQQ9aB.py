"""Independent check — ZigZag Elliott Wave Strategy (qNLQQ9aB): hourly bars of a stock-style symbol, market orders at the next open, fixed quantity 10 on the pinelib side (the original sizes 10 % of equity), pyramiding 1, commission / slippage / margin off.
Pivots (left strictly lower / right not higher; mirrored for lows) over L bars each side give the last low / high; when high > low they set wave 1; wave-2 zone = 50 % - 61.8 % retracement from the wave-1 high; wave-3 target = low + 1.618 x range. A close in the zone while flat buys; a close in the wave-4 band while long tries to add (rejected at pyramiding 1);
close >= 90 % of the target while long closes half of the remaining position every bar; close >= target closes everything. Uses the quantity-aware bracket reference (indep.simulate_brackets with partial closes), comparing quantities too.
Variants: defaults; length 6; length 8 with zone 0.4-0.7 and extension 1.272."""
import numpy as np

from indep import bars, compare_q, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "qNLQQ9aB"
QTY = 10.0


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
    ph, pl = pivots(h, p["len"], True), pivots(l, p["len"], False)
    S = dict(ll=np.nan, lh=np.nan, w1l=np.nan, w1h=np.nan)

    def orders(i, info):
        out = []
        pos = info["pos"]
        if not np.isnan(pl[i]):
            S["ll"] = pl[i]
        if not np.isnan(ph[i]):
            S["lh"] = ph[i]
        if not np.isnan(S["ll"]) and not np.isnan(S["lh"]) and S["lh"] > S["ll"]:
            S["w1l"], S["w1h"] = S["ll"], S["lh"]
        rng = S["w1h"] - S["w1l"]
        with np.errstate(invalid="ignore"):
            f_hi = S["w1h"] - rng * p["rmin"]
            f_lo = S["w1h"] - rng * p["rmax"]
            if c[i] <= f_hi and c[i] >= f_lo and pos == 0:
                out.append(("entry", "Wave 3 Long", 1, QTY))
            tgt = S["w1l"] + rng * p["ext"]
            w4a, w4b = tgt - rng * 0.382, tgt - rng * 0.50
            if c[i] <= w4a and c[i] >= w4b and pos > 0:
                out.append(("entry", "Wave 4 Add", 1, QTY))
            if c[i] >= tgt * 0.90 and pos > 0:
                out.append(("close", "Wave 3 Long", 50.0))
            if c[i] >= tgt:
                out.append(("close_all",))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, qty_step=0.01)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=0.01)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(len=12, rmin=0.50, rmax=0.618, ext=1.618)


def check():
    df = bars(30000, seed=301, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({}, {}), ({"ZigZag Length": 6}, dict(len=6)),
             ({"ZigZag Length": 8, "Wave 2 Min Retracement": 0.4, "Wave 2 Max Retracement": 0.7, "Wave 3 Extension": 1.272}, dict(len=8, rmin=0.4, rmax=0.7, ext=1.272)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
