"""Independent check — Stepped trailing strategy example (jjhUHcje): 6000 daily business-day bars (price ~100) of a stock-style symbol, 1 contract per entry, market orders at the next open, commission / slippage off.
A 14/28 SMA cross-over enters long; the exit order "x" follows the stage machine (1: loss / profit-3 ticks, 2: break-even stop + profit-3, 3: stop at the TP1 level with profit-3 ticks or, with the third-stage trailing option, a trailing stop with activation TP3 and offset TP3 - TP2), with the percentages of the average price converted to ticks. Uses the quantity-aware bracket reference (indep.simulate_brackets with tick-form exits and trailing legs). Variants: defaults; 2 / 2 / 4 / 6 % with the trailing third stage; 3 / 1 / 2 / 3 % fixed third stage."""
import numpy as np

from indep import bars, compare_q, np_sma, np_cross_over, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "jjhUHcje"
MT = 0.01


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    cu = np_cross_over(np_sma(c, 14), np_sma(c, 28))
    S = dict(stage=0)

    def orders(i, info):
        out = []
        pos, avg = info["pos"], info["avg"]
        if cu[i]:
            out.append(("entry", "My Long Entry Id", 1, 1.0))
        pts = lambda pct: avg * pct / 100 / MT
        sl, tp1, tp2, tp3 = pts(p["sl"]), pts(p["tp1"]), pts(p["tp2"]), pts(p["tp3"])
        cur = (h[i] - avg) / MT if pos > 0 else 0.0
        if pos == 0:
            S["stage"] = 0
        if S["stage"] == 0 and pos != 0:
            S["stage"] = 1
        elif S["stage"] == 1 and cur >= tp1:
            S["stage"] = 2
        elif S["stage"] == 2 and cur >= tp2:
            S["stage"] = 3
        st = S["stage"]
        if st == 1:
            out.append(("exit", "x", "", None, None, None, None, None, None, tp3, sl))
        elif st == 2:
            out.append(("exit", "x", "", None, avg, None, None, None, None, tp3, None))
        elif st == 3:
            stop = avg + tp1 * MT
            if p["trail"]:
                out.append(("exit", "x", "", None, stop, None, tp3, None, tp3 - tp2))
            else:
                out.append(("exit", "x", "", None, stop, None, None, None, None, tp3, None))
        else:
            out.append(("cancel", "x"))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=MT, qty_step=1e-9)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params, strategy_overrides={"margin_long": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


def check():
    df = bars(6000, seed=111, freq="B")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.4
    msgs, allok = [], True
    cases = (({}, dict(sl=5, tp1=5, tp2=10, tp3=15, trail=False)),
             ({"stop loss %%": 2, "take profit 1 %%": 2, "take profit 2 %%": 4, "take profit 3 %%": 6, "activate trailing on third stage (tp3 is amount, tp2 is offset level)": True},
              dict(sl=2, tp1=2, tp2=4, tp3=6, trail=True)),
             ({"stop loss %%": 3, "take profit 1 %%": 1, "take profit 2 %%": 2, "take profit 3 %%": 3}, dict(sl=3, tp1=1, tp2=2, tp3=3, trail=False)))
    for params, ov in cases:
        ok, m = one(df, params, ov)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
