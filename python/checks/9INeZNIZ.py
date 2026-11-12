"""Independent check — PEM Terminator2 (9INeZNIZ): 5-minute bars (24 h synthetic, NQ-style price ~15000, 0.25 tick) on a CME futures symbol (VWAP restarts at the 17:00 Chicago session start), market orders at the next open, 6 contracts, commission / slippage / margin off.
State machine restated statement by statement (impulse -> compression box of small candles, at least N stall bars, reset after 15 -> break with a clean body fires a direction; the next bar must confirm it by its colour and sit on the right side of the slow EMA and the VWAP). While in a position every bar re-issues three exit orders of 2 contracts each from the average entry price:
TP1 and TP2 limits in points, and a runner with a trailing stop (activation = offset = 4 ticks per point of the trail input), plus the optional stop. Uses the quantity-aware bracket reference (indep.simulate_brackets), which also compares the closed quantities.
Variants: defaults with a loose stall / compression setting; stop-loss on, TP1 6 / TP2 14 points, trail 8 points, minimum 2 stall bars."""
import numpy as np

from indep import bars, compare_q, np_atr, np_ema, np_vwap, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "9INeZNIZ"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sym = SymbolInfo.make("CME_MINI:NQ1!", "futures", mintick=0.25, qty_step=1e-9)
    tick = 0.25
    es = np_ema(c, 55)
    vw = np_vwap(df, (h + l + c) / 3, start_minutes=17 * 60, tz="America/Chicago")
    atr = np_atr(h, l, c, 14)
    S = dict(state=0, ch=np.nan, cl=np.nan, stall=0, fbar=None, fl=False, fs=False)

    def orders(i, info):
        rng = h[i] - l[i]
        body = abs(c[i] - o[i])
        bf = body / rng if rng > 0 else 0.0
        with np.errstate(invalid="ignore"):
            su, sd = c[i] > o[i] and rng > atr[i] * p["imp"], c[i] < o[i] and rng > atr[i] * p["imp"]
            small = rng < atr[i] * p["comp"]
        if S["state"] == 0 and (su or sd):
            S.update(state=1, stall=0, ch=np.nan, cl=np.nan)
        if S["state"] == 1 and small:
            S.update(state=2, stall=1, ch=h[i], cl=l[i])
        if S["state"] == 2 and small:
            S["stall"] += 1
            S["ch"], S["cl"] = max(S["ch"], h[i]), min(S["cl"], l[i])
        valid = S["state"] == 2 and S["stall"] >= p["stall"]
        bb, br = valid and c[i] > S["ch"], valid and c[i] < S["cl"]
        fire = (bb or br) and bf >= p["body"]
        if fire:
            S.update(fl=bool(bb), fs=bool(br), fbar=i, state=0, stall=0, ch=np.nan, cl=np.nan)
        if S["state"] != 0 and S["stall"] > 15:
            S.update(state=0, stall=0, ch=np.nan, cl=np.nan)
        confirm = S["fbar"] is not None and i == S["fbar"] + 1
        with np.errstate(invalid="ignore"):
            gl = confirm and S["fl"] and c[i] > o[i] and c[i] > es[i] and c[i] > vw[i] and info["pos"] == 0
            gs = confirm and S["fs"] and c[i] < o[i] and c[i] < es[i] and c[i] < vw[i] and info["pos"] == 0
        out = []
        if gl:
            out.append(("entry", "Long", 1, 6.0))
        if gs:
            out.append(("entry", "Short", -1, 6.0))
        pos, ep = info["pos"], info["avg"]
        tr = p["trail"] * 4
        if pos > 0:
            sl = ep - p["slp"] if p["sl"] else None
            out += [("exit", "TP1-L", "Long", ("qty", 2.0), sl, ep + p["t1"]), ("exit", "TP2-L", "Long", ("qty", 2.0), sl, ep + p["t2"]),
                    ("exit", "Run-L", "Long", ("qty", 2.0), sl, None, tr, None, tr)]
        if pos < 0:
            sl = ep + p["slp"] if p["sl"] else None
            out += [("exit", "TP1-S", "Short", ("qty", 2.0), sl, ep - p["t1"]), ("exit", "TP2-S", "Short", ("qty", 2.0), sl, ep - p["t2"]),
                    ("exit", "Run-S", "Short", ("qty", 2.0), sl, None, tr, None, tr)]
        return out

    ref = simulate_brackets(o, h, l, c, orders, tick=tick)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(imp=1.1, comp=0.7, stall=2, body=0.20, sl=False, slp=60.0, t1=10.0, t2=25.0, trail=20.0)


def check():
    df = bars(40000, seed=121, freq="5min")
    base = df["close"].iloc[0]
    for k in ("open", "high", "low", "close"):
        df[k] = 15000 * (df[k] / base) ** 0.05
    msgs, allok = [], True
    cases = (({"Compression Tightness %": 1.0, "Impulse Strength (ATR)": 0.9, "Min Body % (Break)": 0.1}, dict(comp=1.0, imp=0.9, body=0.1)),
             ({"Use Stop Loss?": True, "Stop Loss (NQ points) - ignored if above is false": 15.0, "TP1 (NQ points) - 2 contracts": 6.0, "TP2 (NQ points) - 2 contracts": 14.0,
               "Runner Trailing Stop (NQ points)": 8.0, "Compression Tightness %": 1.0, "Impulse Strength (ATR)": 0.9, "Min Body % (Break)": 0.1},
              dict(sl=True, slp=15.0, t1=6.0, t2=14.0, trail=8.0, comp=1.0, imp=0.9, body=0.1)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
