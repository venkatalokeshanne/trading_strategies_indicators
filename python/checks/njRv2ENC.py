"""Independent check — Supertrend with Entry, TP1, TP2 and TP3 (njRv2ENC): 4000 daily business-day bars (price ~100) of a stock-style symbol, 100 shares per entry (the 100 %-of-equity sizing replaced), market orders at the next open, commission / slippage off.
Supertrend(2.5, 14) direction flips (the reference algorithm), the signal-bar close with a 1.5 ATR stop and 1 R / 2 R / 3 R targets, the flip close of the opposite side, the three partial exit orders sharing the stop (50 % of the position, 25 % of the original, the rest) re-issued every bar with the latest levels, and the optional date window are restated bar by bar.
Uses the quantity-aware bracket reference (indep.simulate_brackets with partial exit legs). Variants: defaults; wider factor 3.5 with the stop at 0.8 ATR, 40 % / 40 % legs and a date window."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_supertrend, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "njRv2ENC"
QTY = 100.0


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    t = df["time"].to_numpy()
    _, d = np_supertrend(h, l, c, p["factor"], 14)
    atr = np_atr(h, l, c, 14)
    S = dict(sl=np.nan, t1=np.nan, t2=np.nan, t3=np.nan)

    def orders(i, info):
        out = []
        pos = info["pos"]
        buy = i > 0 and d[i - 1] >= 0 and d[i] < 0
        sell = i > 0 and d[i - 1] <= 0 and d[i] > 0
        inw = (not p["win"]) or (p["w0"] <= t[i] <= p["w1"])
        if buy and inw:
            e = c[i]
            S["sl"] = e - atr[i] * p["sl"]
            r = e - S["sl"]
            S["t1"], S["t2"], S["t3"] = e + r * 1.0, e + r * 2.0, e + r * 3.0
        if sell and inw:
            e = c[i]
            S["sl"] = e + atr[i] * p["sl"]
            r = S["sl"] - e
            S["t1"], S["t2"], S["t3"] = e - r * 1.0, e - r * 2.0, e - r * 3.0
        if buy and inw:
            out += [("close", "Short"), ("entry", "Long", 1, QTY)]
        if sell and inw:
            out += [("close", "Long"), ("entry", "Short", -1, QTY)]
        nn = lambda x: None if np.isnan(x) else float(x)
        if pos > 0:
            out += [("exit", "Long TP1/SL", "Long", p["q1"], nn(S["sl"]), nn(S["t1"])), ("exit", "Long TP2/SL", "Long", p["q2"], nn(S["sl"]), nn(S["t2"])), ("exit", "Long TP3/SL", "Long", None, nn(S["sl"]), nn(S["t3"]))]
        if pos < 0:
            out += [("exit", "Short TP1/SL", "Short", p["q1"], nn(S["sl"]), nn(S["t1"])), ("exit", "Short TP2/SL", "Short", p["q2"], nn(S["sl"]), nn(S["t2"])), ("exit", "Short TP3/SL", "Short", None, nn(S["sl"]), nn(S["t3"]))]
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=0.01, qty_step=1e-9)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, dd = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params,
                                      strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{dd} (got {len(ref)})"


def check():
    df = bars(4000, seed=5, freq="B")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    w0, w1 = int(df["time"].iloc[800]), int(df["time"].iloc[2800])
    msgs, allok = [], True
    cases = (({}, dict(factor=2.5, sl=1.5, q1=50.0, q2=25.0, win=False, w0=0, w1=0)),
             ({"Factor": 3.5, "SL ATR Multiplier": 0.8, "TP1 Exit %": 40, "TP2 Exit %": 40, "Limit Backtest Date Range": True, "Start Date": w0, "End Date": w1},
              dict(factor=3.5, sl=0.8, q1=40.0, q2=40.0, win=True, w0=w0, w1=w1)))
    for params, ov in cases:
        ok, m = one(df, params, ov)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
