"""Independent check — Velocity Breakout Strategy (m1JDhFR9): 15-minute bars (24 h synthetic, drift-free, price ~100) of a stock-style symbol, 10 shares per entry (the 100 %-of-equity sizing replaced), market orders at the next open, commission / slippage off.
EMA 9/20/50, DMI(14) ADX, ATR(10/14/50), the 100-bar dealing range discount, the ADX-squeeze ATR multiplier (once profitable), the UT-Bot-style trailing stop recursion with its +1/-1 position state, the master-candle consolidation state, the golden / death crosses, the macro-bearish-low higher-low rule, the run-up filter, the armed reload with the EMA touch / shift / sweep, and the four entries (taken while flat) with the trail-flip and death-cross closes are restated bar by bar.
Uses the quantity-aware bracket reference (indep.simulate_brackets). Variants: defaults; strict higher-low off with the chop block on and a 3-bar consolidation."""
import numpy as np

from indep import bars, compare_q, np_atr, np_cross_over, np_cross_under, np_dmi, np_ema, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "m1JDhFR9"
QTY = 10.0


def wfn(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    fe, se = np_ema(c, 20), np_ema(c, 50)
    _, _, adx = np_dmi(h, l, c, 14)
    a14, a50, a10 = np_atr(h, l, c, 14), np_atr(h, l, c, 50), np_atr(h, l, c, 10)
    drh, drl = wfn(h, 100, np.max), wfn(l, 100, np.min)
    gc, dc = np_cross_over(fe, se), np_cross_under(fe, se)
    rl = wfn(l, 12, np.min)
    hi5 = wfn(h, 5, np.max)
    lo4 = wfn(l, 4, np.min)
    S = dict(x=0.0, pos=0, mtop=np.nan, mbot=np.nan, inside=0, armed=False, mbl=l[0], barmed=True)

    def orders(i, info):
        out = []
        ps, avg = info["pos"], info["avg"]
        with np.errstate(invalid="ignore"):
            tight = a14[i] < a50[i]
            bullc = c[i] >= o[i]
            ueq = drl[i] + (drh[i] - drl[i]) * 0.60
            indisc = c[i] <= ueq
            bt = fe[i] > se[i]
            profit = ps > 0 and c[i] > avg
            squeeze = bool(adx[i] < 20 and profit)
            nloss = (1.5 if squeeze else 3.0) * a10[i]
        prev = S["x"]
        c1 = c[i - 1] if i else np.nan
        with np.errstate(invalid="ignore"):
            if c[i] > prev and c1 > prev:
                x = max(prev, c[i] - nloss)
            elif c[i] < prev and c1 < prev:
                x = min(prev, c[i] + nloss)
            elif c[i] > prev:
                x = c[i] - nloss
            else:
                x = c[i] + nloss
            pos_prev = S["pos"]
            if c1 < prev and c[i] > prev:
                S["pos"] = 1
            elif c1 > prev and c[i] < prev:
                S["pos"] = -1
        S["x"] = 0.0 if np.isnan(x) else x
        green = S["pos"] == 1
        vt = (bt and green) if p["strict_brk"] else True
        brk = S["armed"] and c[i] > S["mtop"] and bullc and vt
        take_brk = bool(brk and ((not p["chop"]) or not tight))
        with np.errstate(invalid="ignore"):
            if np.isnan(S["mtop"]) or c[i] > S["mtop"] or c[i] < S["mbot"]:
                S["mtop"], S["mbot"], S["inside"], S["armed"] = h[i], l[i], 0, False
            else:
                S["inside"] += 1
        if S["inside"] >= p["consol"]:
            S["armed"] = True
        if dc[i]:
            S["mbl"] = l[i]
        if not bt:
            S["mbl"] = min(S["mbl"], l[i])
        with np.errstate(invalid="ignore"):
            hl = rl[i] > S["mbl"]
            vstruct = hl if p["strict_aplus"] else True
            runup = (c[i] - rl[i]) / rl[i] * 100
            vchase = runup <= 10.0
            chopok = (not p["chop"]) or not tight
            t_long = bool(gc[i] and vstruct and vchase and chopok)
            t_risky = bool(gc[i] and (not vstruct) and (not p["strict_aplus"]) and vchase and chopok)
        hp = hi5[i - 1] if i else np.nan
        with np.errstate(invalid="ignore"):
            if c[i] > hp:
                S["barmed"] = True
            body = abs(c[i] - o[i])
            lw = min(o[i], c[i]) - l[i]
            sweep = bool(lw > body * 1.5 and bullc)
            touched = bool(lo4[i] <= fe[i])
            shift = bool(c[i] > fe[i] and bullc)
            reload = bool(bt and S["barmed"] and touched and indisc and (shift or sweep) and green and (not gc[i]) and chopok)
        if reload:
            S["barmed"] = False
        if (t_long or t_risky or reload or take_brk) and ps == 0:
            out.append(("entry", "Long", 1, QTY))
        if S["pos"] == -1 and pos_prev == 1:
            out.append(("close", "Long"))
        if dc[i]:
            out.append(("close", "Long"))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=0.01, qty_step=1e-9)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, dd = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                      strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{dd} (got {len(ref)})"


def check():
    df = bars(40000, seed=5, freq="15min")
    lc = np.log(df["close"].to_numpy() / 100)
    det = lc - np.polyval(np.polyfit(np.arange(len(lc)), lc, 1), np.arange(len(lc)))
    rel = {k: df[k].to_numpy() / df["close"].to_numpy() for k in ("open", "high", "low", "close")}
    for k in rel:
        df[k] = 100 * np.exp(0.4 * det) * rel[k] ** 0.4
    msgs, allok = [], True
    cases = (({}, dict(strict_brk=True, chop=False, strict_aplus=True, consol=4)),
             ({"Require Higher Low for A+ Entry": False, "Block Entries in Gray Chop Zone": True, "Required Follow-up Bars": 3}, dict(strict_brk=True, chop=True, strict_aplus=False, consol=3)))
    for params, ov in cases:
        ok, m = one(df, params, ov)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
