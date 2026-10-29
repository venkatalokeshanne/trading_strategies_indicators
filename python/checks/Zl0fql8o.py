"""Independent check — VWAP Trend Momentum [Artillery] (Zl0fql8o): 5-minute bars (24 h synthetic, price ~100) of a stock-style symbol (daily periods from 09:30 New York), market orders at the next open, quantity 1, commission / slippage / margin off.
Session VWAP accumulated from the daily-period start (volume floored at 1); EMA(34) slope over 3 bars beyond 5 % of the ATR, close over VWAP and EMA50 (shorts mirrored); near-VWAP within the pull-back % in any of the last four bars; bounce = the close beyond VWAP and beyond the previous high / low; trades per day capped; window 09:45 - 15:30 ET.
The entry stores ATR stop / target; one exit order per side with the stored levels is re-issued each bar of a position (stop raised to the entry when the break-even trigger is met); flatten when the session end is crossed. Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too.
Variants: defaults with the EMA50 and pull-back loosened (0.5 %); long only with break-even 1.0 ATR and TP 3."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_ema, np_periods, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "Zl0fql8o"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    now = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    insess = (now >= 585) & (now < 930)
    send = np.r_[False, (now[1:] >= 930) & (now[:-1] < 930)]
    pid, _ = np_periods(df, 1440)
    e34, e50, atr = np_ema(c, 34), np_ema(c, 50), np_atr(h, l, c, 14)
    slope = e34 - np.r_[np.full(3, np.nan), e34[:-3]]
    S = dict(num=0.0, den=0.0, tc=0, ent=np.nan, sl=np.nan, tp=np.nan, near=[False, False, False, False])

    def orders(i, info):
        out = []
        pos = info["pos"]
        nd = i > 0 and pid[i] != pid[i - 1]
        if nd:
            S["num"] = S["den"] = 0.0
            S["tc"] = 0
        vf = max(v[i], 1.0)
        S["num"] += (h[i] + l[i] + c[i]) / 3.0 * vf
        S["den"] += vf
        vw = S["num"] / S["den"]
        with np.errstate(invalid="ignore"):
            sok = not np.isnan(atr[i]) and abs(slope[i]) > atr[i] * 0.05
            e50l = (not p["e50"]) or c[i] > e50[i]
            e50s = (not p["e50"]) or c[i] < e50[i]
            bull = c[i] > vw and slope[i] > 0 and sok and e50l
            bear = c[i] < vw and slope[i] < 0 and sok and e50s and not p["lo"]
            nv = abs(c[i] - vw) / c[i] * 100 <= p["pb"]
        was = nv or S["near"][0] or S["near"][1] or S["near"][2]
        S["near"] = [nv, S["near"][0], S["near"][1], S["near"][2]]
        hp, lp = (h[i - 1], l[i - 1]) if i > 0 else (np.nan, np.nan)
        with np.errstate(invalid="ignore"):
            bl = was and c[i] > vw and c[i] > hp
            bs = was and c[i] < vw and c[i] < lp
            can = S["tc"] < 3 and pos == 0 and insess[i] and not np.isnan(atr[i]) and atr[i] > 0
            gl, gs = can and bull and bl, can and bear and bs
        if gl or gs:
            S["ent"] = c[i]
        if gl:
            S["sl"], S["tp"] = c[i] - atr[i] * 1.5, c[i] + atr[i] * p["tp"]
        elif gs:
            S["sl"], S["tp"] = c[i] + atr[i] * 1.5, c[i] - atr[i] * p["tp"]
        if gl:
            out.append(("entry", "Long", 1, 1.0))
            S["tc"] += 1
        if gs:
            out.append(("entry", "Short", -1, 1.0))
            S["tc"] += 1
        with np.errstate(invalid="ignore"):
            bel = pos > 0 and h[i] >= S["ent"] + atr[i] * p["be"]
            bes = pos < 0 and l[i] <= S["ent"] - atr[i] * p["be"]
            if bel:
                S["sl"] = max(S["sl"], S["ent"])
            elif bes:
                S["sl"] = min(S["sl"], S["ent"])
        if pos > 0:
            out.append(("exit", "XL", "Long", None, S["sl"], S["tp"]))
        if pos < 0:
            out.append(("exit", "XS", "Short", None, S["sl"], S["tp"]))
        if send[i] and pos != 0:
            out.append(("close_all",))
        return out

    ref = simulate_brackets(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(e50=True, pb=0.15, lo=False, tp=4.5, be=99.0)


def check():
    df = bars(60000, seed=661, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.1
    msgs, allok = [], True
    cases = (({"Require price beyond EMA50": False, "Max pullback to VWAP %": 0.5}, dict(e50=False, pb=0.5)),
             ({"Long only": True, "Breakeven trigger x ATR (99=off)": 1.0, "TP x ATR": 3.0, "Max pullback to VWAP %": 0.5}, dict(lo=True, be=1.0, tp=3.0, pb=0.5)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
