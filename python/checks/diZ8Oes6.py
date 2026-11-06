"""Independent check — EMA & Fib Confluence with 3 Targets + Trailing (diZ8Oes6): hourly bars, market orders at the next open, fixed quantity 10 on the pinelib side (the original sizes 100 % of equity), commission / slippage / margin off.
The Pine state machine is restated statement by statement: confluence = EMA fast over slow and the close crossing over the retracement level of the lookback high-low range (mirror for shorts); a signal with the tracker at 0 sets targets / trailing level and the tracker, enters; the target / trailing block needs the tracker AND the position;
the last statement zeroes the tracker whenever the position is flat at script time (including the signal bar, since the entry fills at the next open). Reference: indep.simulate_brackets (3 partial limit exits of 33 / 33 / 34 %, market close), comparing quantities too.
Variants: defaults; EMAs 5 / 13, lookback 20, ratio 0.5; wider targets and trailing."""
import numpy as np

from indep import bars, compare_q, np_cross_over, np_cross_under, np_ema, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "diZ8Oes6"
QTY = 10.0


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ef, es = np_ema(c, p["f"]), np_ema(c, p["s"])
    hh = np.array([h[max(0, i - p["lb"] + 1):i + 1].max() if i >= p["lb"] - 1 else np.nan for i in range(n)])
    ll = np.array([l[max(0, i - p["lb"] + 1):i + 1].min() if i >= p["lb"] - 1 else np.nan for i in range(n)])
    rng = hh - ll
    fibl, fibs = hh - rng * p["ratio"], ll + rng * p["ratio"]
    with np.errstate(invalid="ignore"):
        xo, xu = np_cross_over(c, fibl), np_cross_under(c, fibs)
        eu, ed = np_cross_over(ef, es), np_cross_under(ef, es)
        buy = (ef > es) & xo
        sell = (ef < es) & xu
    S = dict(apt=0, t=[np.nan] * 3, trail=np.nan)

    def orders(i, info):
        out = []
        pos = info["pos"]
        if buy[i] and S["apt"] == 0:
            S["t"] = [c[i] * (1 + p["tp1"] / 100), c[i] * (1 + p["tp2"] / 100), c[i] * (1 + p["tp3"] / 100)]
            S["trail"] = c[i] * (1 - p["trail"] / 100)
            S["apt"] = 1
            out.append(("entry", "Long", 1, QTY))
        if sell[i] and S["apt"] == 0:
            S["t"] = [c[i] * (1 - p["tp1"] / 100), c[i] * (1 - p["tp2"] / 100), c[i] * (1 - p["tp3"] / 100)]
            S["trail"] = c[i] * (1 + p["trail"] / 100)
            S["apt"] = -1
            out.append(("entry", "Short", -1, QTY))
        if pos > 0 and S["apt"] == 1:
            out += [("exit", "T1 Long", "Long", 33, None, S["t"][0]), ("exit", "T2 Long", "Long", 33, None, S["t"][1]), ("exit", "T3 Long", "Long", 34, None, S["t"][2])]
            if c[i] * (1 - p["trail"] / 100) > S["trail"]:
                S["trail"] = c[i] * (1 - p["trail"] / 100)
            if c[i] <= S["trail"] or ed[i]:
                out.append(("close", "Long"))
                S["apt"] = 0
        if pos < 0 and S["apt"] == -1:
            out += [("exit", "T1 Short", "Short", 33, None, S["t"][0]), ("exit", "T2 Short", "Short", 33, None, S["t"][1]), ("exit", "T3 Short", "Short", 34, None, S["t"][2])]
            if c[i] * (1 + p["trail"] / 100) < S["trail"]:
                S["trail"] = c[i] * (1 + p["trail"] / 100)
            if c[i] >= S["trail"] or eu[i]:
                out.append(("close", "Short"))
                S["apt"] = 0
        if pos == 0:
            S["apt"] = 0
        return out

    ref = simulate_brackets(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(f=9, s=21, lb=50, ratio=0.618, tp1=1.0, tp2=2.0, tp3=3.5, trail=1.5)


def check():
    df = bars(30000, seed=101, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Fast EMA Length": 5, "Slow EMA Length": 13, "Fibonacci Lookback Period": 20, "Fib Entry Target Ratio": 0.5}, dict(f=5, s=13, lb=20, ratio=0.5)),
             ({"Target 1 (%)": 2.0, "Target 2 (%)": 4.0, "Target 3 (%)": 7.0, "Trailing Distance (%)": 3.0}, dict(tp1=2.0, tp2=4.0, tp3=7.0, trail=3.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
