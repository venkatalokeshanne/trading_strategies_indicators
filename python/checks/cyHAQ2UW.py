"""Independent check — Market Structure Strategy v4 (cyHAQ2UW): hourly bars, market orders at the next open, fixed quantity 10 on the pinelib side (the original sizes 2 % of equity), commission / slippage / margin off.
External pivots (unique extreme over N bars each side) set the bias (close beyond the last external high / low); internal pivots give the latest higher low (bias up) / lower high (bias down); the pullback zone is 30 % - 85 % of the range between the external extreme and that internal swing;
a bar whose low (high) trades inside the zone with ADX above the minimum enters; the stop is the internal swing -/+ ATR x buffer, the 1R and 1.8R targets sit around the signal close. Two exit orders per entry, 50 % of the entry quantity each, same stop, re-issued at every new entry (pyramiding 3).
Uses the quantity-aware bracket reference (indep.simulate_brackets), which also compares the closed quantities.
Variants: defaults; shorter structure lengths and loose ADX; targets 0.8R / 2.5R, pyramiding stays 3."""
import numpy as np

from indep import bars, compare_q, np_atr, np_dmi, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "cyHAQ2UW"
QTY = 10.0


def pivots(x, k, high):
    n = len(x)
    out = np.full(n, np.nan)
    for i in range(2 * k, n):
        m = i - k
        win = x[m - k:m + k + 1]
        ext = win.max() if high else win.min()
        if x[m] == ext and (win == x[m]).sum() == 1:
            out[i] = x[m]
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr = np_atr(h, l, c, 14)
    _, _, adx = np_dmi(h, l, c, 14)
    eh, el = pivots(h, p["ext"], True), pivots(l, p["ext"], False)
    ih, il = pivots(h, p["int"], True), pivots(l, p["int"], False)
    S = dict(leh=np.nan, lel=np.nan, bias=0, hl=np.nan, lh=np.nan)

    def orders(i, info):
        if not np.isnan(eh[i]):
            S["leh"] = eh[i]
        if not np.isnan(el[i]):
            S["lel"] = el[i]
        if not np.isnan(S["leh"]) and c[i] > S["leh"]:
            S["bias"] = 1
        if not np.isnan(S["lel"]) and c[i] < S["lel"]:
            S["bias"] = -1
        if S["bias"] == 1 and not np.isnan(il[i]):
            S["hl"] = il[i]
        if S["bias"] == -1 and not np.isnan(ih[i]):
            S["lh"] = ih[i]
        top = bot = np.nan
        if S["bias"] == 1 and not np.isnan(S["hl"]) and not np.isnan(S["leh"]):
            r = S["leh"] - S["hl"]
            top, bot = S["leh"] - r * 0.30, S["leh"] - r * 0.85
        if S["bias"] == -1 and not np.isnan(S["lh"]) and not np.isnan(S["lel"]):
            r = S["lh"] - S["lel"]
            bot, top = S["lel"] + r * 0.30, S["lel"] + r * 0.85
        out = []
        with np.errstate(invalid="ignore"):
            long_ok = S["bias"] == 1 and adx[i] > p["adx"] and l[i] <= top and l[i] >= bot
            short_ok = S["bias"] == -1 and adx[i] > p["adx"] and h[i] >= bot and h[i] <= top
        if long_ok and not np.isnan(S["hl"]):
            stop = S["hl"] - atr[i] * 0.4
            risk = c[i] - stop
            out += [("entry", "Long", 1, QTY), ("exit", "L-P1", "Long", 50, stop, c[i] + risk * p["r1"]), ("exit", "L-P2", "Long", 50, stop, c[i] + risk * p["r2"])]
        if short_ok and not np.isnan(S["lh"]):
            stop = S["lh"] + atr[i] * 0.4
            risk = stop - c[i]
            out += [("entry", "Short", -1, QTY), ("exit", "S-P1", "Short", 50, stop, c[i] - risk * p["r1"]), ("exit", "S-P2", "Short", 50, stop, c[i] - risk * p["r2"])]
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=3)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(ext=15, int=4, adx=15.0, r1=1.0, r2=1.8)


def check():
    df = bars(30000, seed=51, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({}, {}),
             ({"External Structure Length": 8, "Internal Structure Length": 3, "Minimum ADX (Loose!)": 5.0}, dict(ext=8, int=3, adx=5.0)),
             ({"Partial Profit R": 0.8, "Final Target R": 2.5}, dict(r1=0.8, r2=2.5)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
