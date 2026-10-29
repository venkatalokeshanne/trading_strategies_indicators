"""Independent check — Slope & MA Cross + Acc + Range Filter (MqmIh0D9): hourly bars of a stock-style symbol, market orders at the next open, default quantity 1, commission / slippage / margin off.
MA (Hull: WMA(2 WMA(c, n/2) - WMA(c, n), round(sqrt(n))), or EMA) -> slope = MA - MA[lookback], acceleration = slope - slope[1], angle = degrees(atan(slope % x multiplier)); range filter needs |angle| >= minimum. Entries (default): acceleration zero-cross, plus the re-entry (close crossing the previous bar's high/low inside a slope/price-confirmed trend);
exits on slope/price/acceleration reverse crosses. Per-bar exit orders: percentage stop (tightened by the shrinking stop when the bar's profit passes the minimum and the slope decelerates) and the trailing stop (activation price = entry x (1 + start), offset = round(entry x distance / tick) ticks).
Uses the quantity-aware bracket reference (indep.simulate_brackets with trailing legs), comparing quantities too. Variants: defaults with a loose range filter (angle 5, multiplier 100); EMA 30 with the shrinking stop off and TP 2 %; Hull 30 with trailing off."""
import math

import numpy as np

from indep import bars, compare_q, np_cross_over, np_cross_under, np_ema, np_wma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "MqmIh0D9"


def hull(c, n):
    a = np_wma(c, n // 2)
    b = np_wma(c, n)
    return np_wma(2 * a - b, int(math.floor(math.sqrt(n) + 0.5)))


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ma = hull(c, p["len"]) if p["ma"] == "Hull MA" else np_ema(c, p["len"])
    back = np.r_[np.full(1, np.nan), ma[:-1]]
    slope = ma - back
    slope1 = np.r_[np.nan, slope[:-1]]
    acc = slope - slope1
    with np.errstate(invalid="ignore", divide="ignore"):
        ang = np.degrees(np.arctan((ma - back) / back * 100 * p["mult"]))
    zero = np.zeros(n)
    s_up, s_dn = np_cross_over(slope, zero), np_cross_under(slope, zero)
    p_up, p_dn = np_cross_over(c, ma), np_cross_under(c, ma)
    a_up, a_dn = np_cross_over(acc, zero), np_cross_under(acc, zero)
    hp, lp = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    r_up, r_dn = np_cross_over(c, hp), np_cross_under(c, lp)
    tick = 0.01
    S = dict(sl=np.nan, ss=np.nan, last=-1)

    def orders(i, info):
        out = []
        pos, avg = info["pos"], info["avg"]
        with np.errstate(invalid="ignore"):
            tl = (ang[i] >= p["ang"]) if p["rf"] else True
            ts = (ang[i] <= -p["ang"]) if p["rf"] else True
            lt = slope[i] > 0 and c[i] > ma[i]
            st_ = slope[i] < 0 and c[i] < ma[i]
            lcs = bool(a_up[i])
            scs = bool(a_dn[i])
            lre = lt and bool(r_up[i])
            sre = st_ and bool(r_dn[i])
            lfin = (lcs or lre) and tl
            sfin = (scs or sre) and ts
            xl = bool(s_dn[i]) or bool(p_dn[i]) or bool(a_dn[i])
            xs = bool(s_up[i]) or bool(p_up[i]) or bool(a_up[i])
            fadel = slope[i] < slope1[i] and slope[i] > 0
            fades = slope[i] > slope1[i] and slope[i] < 0
            tp = (h[i] + l[i] + c[i]) / 3
            slp = p["sl"] / 100
            if pos > 0:
                if (h[i] - avg) / avg >= 0.015 and ((fadel) if p["mom"] else True):
                    cs = max(tp * (1 - slp * 0.5), avg * (1 - slp))
                    S["sl"] = cs if np.isnan(S["sl"]) else max(S["sl"], cs)
            else:
                S["sl"] = np.nan
            if pos < 0:
                if (avg - l[i]) / avg >= 0.015 and ((fades) if p["mom"] else True):
                    cs = min(tp * (1 + slp * 0.5), avg * (1 + slp))
                    S["ss"] = cs if np.isnan(S["ss"]) else min(S["ss"], cs)
            else:
                S["ss"] = np.nan
            fl_ = (max(avg * (1 - slp), S["sl"]) if (p["shr"] and not np.isnan(S["sl"])) else avg * (1 - slp)) if pos > 0 else np.nan
            fs_ = (min(avg * (1 + slp), S["ss"]) if (p["shr"] and not np.isnan(S["ss"])) else avg * (1 + slp)) if pos < 0 else np.nan
        if pos > 0 and xl:
            out.append(("close", "Base MA Long"))
        if pos < 0 and xs:
            out.append(("close", "Base MA Short"))
        if S["last"] != i and pos == 0:
            if lfin:
                out.append(("entry", "Base MA Long", 1, 1.0))
                S["last"] = i
            elif sfin:
                out.append(("entry", "Base MA Short", -1, 1.0))
                S["last"] = i
        nn = lambda x: None if np.isnan(x) else x
        tpl = avg * (1 + p["tpp"] / 100) if p["utp"] else None
        tps = avg * (1 - p["tpp"] / 100) if p["utp"] else None
        off = max(1, math.floor(avg * 0.01 / tick + 0.5)) if not np.isnan(avg) else None
        if p["tr"] and not np.isnan(avg):
            tl_ = (None, avg * (1 + 0.015), off)
            ts_ = (None, avg * (1 - 0.015), off)
        else:
            tl_ = ts_ = (None, None, None)
        out.append(("exit", "Exit_L", "Base MA Long", None, nn(fl_) if p["sl_on"] else None, nn(tpl) if tpl is not None else None) + tl_)
        out.append(("exit", "Exit_S", "Base MA Short", None, nn(fs_) if p["sl_on"] else None, nn(tps) if tps is not None else None) + ts_)
        return out

    ref = simulate_brackets(o, h, l, c, orders, tick=tick)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(ma="Hull MA", len=100, rf=True, ang=35.0, mult=10.0, sl=1.0, mom=True, shr=True, utp=False, tpp=2.0, tr=True, sl_on=True)


def check():
    df = bars(30000, seed=711, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    loose = {"Minimum Trend Angle (°)": 5.0, "Angle Sensitivity Multiplier": 100.0}
    lo = dict(ang=5.0, mult=100.0)
    cases = ((loose, lo),
             ({**loose, "MA Type": "EMA", "MA Period": 30, "Enable Shrinking SL": False, "Enable Take Profit (TP)": True}, dict(lo, ma="EMA", len=30, shr=False, utp=True)),
             ({**loose, "MA Period": 30, "Enable Trailing Stop": False}, dict(lo, len=30, tr=False)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
