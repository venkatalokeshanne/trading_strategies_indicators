"""Independent check — STtrend - TP Lock Added (N8NUtk99): hourly bars of a stock-style symbol (point value 1), market orders at the next open, quantity 1, commission / slippage / margin off.
Supertrend flips (direction -1 = up) reverse the position (close the other side, enter 1 unit). While in a position every bar re-issues a stop and an optional take-profit from the average entry: the stop = max (min for shorts) of the tracked stop and max(initial stop, lock stop of the highest lock trigger reached by the open profit at the signal close); the tracked stop is cleared only when flat at script time.
A flip against the position also closes it. Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too. Variants: small dollar levels (risk 1.5, locks 0.5 / 1 / 2 with 0.1 / 0.4 / 1, TP 3); wider (risk 3, TP off, locks off)."""
import numpy as np

from indep import bars, compare_q, np_supertrend, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "N8NUtk99"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    _, d = np_supertrend(h, l, c, 3.0, 10)
    d1 = np.r_[np.nan, d[:-1]]
    with np.errstate(invalid="ignore"):
        bf, sf = (d < 0) & (d1 > 0), (d > 0) & (d1 < 0)
    S = dict(act=np.nan)

    def orders(i, info):
        out = []
        pos, avg = info["pos"], info["avg"]
        op = (c[i] - avg) if pos > 0 else ((avg - c[i]) if pos < 0 else 0.0)
        if bf[i]:
            out += [("close", "Short"), ("entry", "Long", 1, 1.0)]
        if sf[i]:
            out += [("close", "Long"), ("entry", "Short", -1, 1.0)]
        if pos != 0:
            locked = 0.0
            if p["locks"]:
                if op >= p["t3"]:
                    locked = p["a3"]
                elif op >= p["t2"]:
                    locked = p["a2"]
                elif op >= p["t1"]:
                    locked = p["a1"]
            ltp = avg + p["tp"] if p["utp"] else None
            stp = avg - p["tp"] if p["utp"] else None
            if pos > 0:
                cand = avg - p["risk"]
                if locked > 0:
                    cand = max(cand, avg + locked)
                S["act"] = cand if np.isnan(S["act"]) else max(S["act"], cand)
                out.append(("exit", "Long Exit", "Long", None, S["act"], ltp))
            if pos < 0:
                cand = avg + p["risk"]
                if locked > 0:
                    cand = min(cand, avg - locked)
                S["act"] = cand if np.isnan(S["act"]) else min(S["act"], cand)
                out.append(("exit", "Short Exit", "Short", None, S["act"], stp))
        else:
            S["act"] = np.nan
        if pos > 0 and sf[i]:
            out.append(("close", "Long"))
        if pos < 0 and bf[i]:
            out.append(("close", "Short"))
        return out

    ref = simulate_brackets(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, dd = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params,
                                      strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{dd} (got {len(ref)})"


def check():
    df = bars(30000, seed=561, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({"Initial Stop Loss ($)": 1.5, "Lock 1 Trigger ($)": 0.5, "Lock 1 Locked Profit ($)": 0.1, "Lock 2 Trigger ($)": 1.0, "Lock 2 Locked Profit ($)": 0.4,
               "Lock 3 Trigger ($)": 2.0, "Lock 3 Locked Profit ($)": 1.0, "Take Profit ($)": 3.0},
              dict(risk=1.5, t1=0.5, a1=0.1, t2=1.0, a2=0.4, t3=2.0, a3=1.0, tp=3.0, locks=True, utp=True)),
             ({"Initial Stop Loss ($)": 3.0, "Enable Hard Take Profit": False, "Enable Profit Locks": False},
              dict(risk=3.0, t1=1500, a1=500, t2=2500, a2=1500, t3=4000, a3=3000, tp=3000, locks=False, utp=False)))
    for params, ov in cases:
        ok, m = one(df, params, ov)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
