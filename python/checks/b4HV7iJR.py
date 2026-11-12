"""Independent check — MM: Optimal F (b4HV7iJR): daily-style bars (3000, price ~100) of a stock-style symbol, market orders at the next open, margin / commission / slippage off.
Supertrend(1, 20) flips: up -> long (when not long) with 1 contract, or equity x f / max loss contracts (optionally rounded down to at least 1) with Optimal-F sizing on; down -> close the long. Equity is mirrored (initial capital + closed P&L + open P&L).
Uses the quantity-aware bracket reference (indep.simulate_brackets). Variants: defaults (1 contract); Optimal-F sizing with f = 0.35 and a 500 max loss; the same rounded down."""
import numpy as np

from indep import bars, compare_q, np_supertrend, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "b4HV7iJR"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    _, d = np_supertrend(h, l, c, 1.0, 20)
    log: list = []

    def orders(i, info):
        out = []
        eq = 100000.0 + sum(dd * (xp - ep) * q for dd, _, ep, _, xp, q in log) + sum(x["d"] * x["q"] * (c[i] - x["ep"]) for x in info["lots"])
        raw = (eq * p["f"] / p["maxloss"] if p["maxloss"] > 0 else 0.0) if p["on"] else 1.0
        size = max(np.floor(raw), 1.0) if p["floor"] else max(raw, 0.0)
        le = i > 0 and d[i] == -1 and d[i - 1] == 1
        se = i > 0 and d[i] == 1 and d[i - 1] == -1
        if le and info["pos"] <= 0 and size > 0:
            out.append(("entry", "Long", 1, float(size)))
        if se:
            out.append(("close", "Long"))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=0.01, qty_step=1e-9, log=log)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, dd = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params, strategy_overrides={"commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{dd} (got {len(ref)})"


def check():
    df = bars(3000, seed=101, freq="B")
    msgs, allok = [], True
    cases = (({}, dict(on=False, floor=False, f=0.21, maxloss=9794.92)),
             ({"Enable Optimal F Position Sizing": True, "Optimal F": 0.35, "Max Loss": 500.0}, dict(on=True, floor=False, f=0.35, maxloss=500.0)),
             ({"Enable Optimal F Position Sizing": True, "Optimal F": 0.35, "Max Loss": 500.0, "Rounds contracts number": True}, dict(on=True, floor=True, f=0.35, maxloss=500.0)))
    for params, ov in cases:
        ok, m = one(df, params, ov)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
