"""Independent check — Gecko ORB Small Range Breakout v1.4 (BPqrxgtc): 5-minute bars (24 h synthetic, price ~100) of a stock-style symbol (New York time), market orders at the next open, default quantity 1, pyramiding 0, commission / slippage / margin off.
Opening range = bars with open time 08:00 - 08:25 NY (first bar seeds high / low / open price); at the first bar after it ends its size / the first open x 100 classifies it (at or above the large threshold = not tradeable). In the entry window 08:25 - 11:00, once per day (flag reset by the next range), a close above the range high / below the range low enters long / short with the stop at the other edge and a limit (R multiple of the entry risk,
ORB projection, or none); from 16:00 NY (once per day, the flag reset by the next range) any position is closed at the next open. Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too. Variants: defaults with a wide large-threshold 3 %; ORB projection TP 1.5; No TP with a 1.5 % small threshold."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "BPqrxgtc"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    orb = (mins >= 480) & (mins < 505)
    ent = (mins >= 505) & (mins < 660)
    ext = mins >= 960
    S = dict(hi=np.nan, lo=np.nan, op=np.nan, drawn=False, done=False, trade=False, exited=False, prev=False)

    def orders(i, info):
        out = []
        first = orb[i] and not S["prev"]
        draw = S["prev"] and not orb[i]
        S["prev"] = bool(orb[i])
        if first:
            S.update(hi=h[i], lo=l[i], op=o[i], drawn=False, done=False, trade=False, exited=False)
        if orb[i]:
            S["hi"], S["lo"] = max(S["hi"], h[i]), min(S["lo"], l[i])
        if draw and not np.isnan(S["hi"]) and not np.isnan(S["lo"]):
            pct = (S["hi"] - S["lo"]) / S["op"] * 100
            S["trade"] = not (pct >= p["large"])
            S["drawn"] = True
        lb = S["drawn"] and S["trade"] and not S["done"] and ent[i] and c[i] > S["hi"]
        sb = S["drawn"] and S["trade"] and not S["done"] and ent[i] and c[i] < S["lo"]
        rng = S["hi"] - S["lo"]
        if lb:
            risk = c[i] - S["lo"]
            tp = c[i] + risk * p["r"] if p["mode"] == "R" else (S["hi"] + rng * p["proj"] if p["mode"] == "P" else None)
            out += [("entry", "Long", 1, 1.0), ("exit", "Long Exit", "Long", None, S["lo"], tp)]
            S["done"] = True
        if sb:
            risk = S["hi"] - c[i]
            tp = c[i] - risk * p["r"] if p["mode"] == "R" else (S["lo"] - rng * p["proj"] if p["mode"] == "P" else None)
            out += [("entry", "Short", -1, 1.0), ("exit", "Short Exit", "Short", None, S["hi"], tp)]
            S["done"] = True
        if ext[i] and not S["exited"]:
            out.append(("close_all",))
            S["exited"] = True
        return out

    ref = simulate_brackets(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(large=1.0, mode="R", r=2.0, proj=2.0)


def check():
    df = bars(60000, seed=531, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.1
    msgs, allok = [], True
    cases = (({"Large ORB threshold %": 3.0, "Small ORB threshold %": 1.0, "R Multiple TP": 0.3}, dict(large=3.0, r=0.3)),
             ({"Large ORB threshold %": 3.0, "Take Profit Mode": "ORB Projection", "ORB Projection Multiplier": 0.2}, dict(large=3.0, mode="P", proj=0.2)),
             ({"Large ORB threshold %": 3.0, "Take Profit Mode": "No TP"}, dict(large=3.0, mode="N")))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
