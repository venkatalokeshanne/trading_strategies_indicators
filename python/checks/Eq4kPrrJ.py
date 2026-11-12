"""Independent check — Golden Trident Swing-Anchored VWAP Trend System (Eq4kPrrJ): 6000 daily business-day bars (price ~100, 09:30 New York stamps) of a stock-style symbol, 10 shares per entry (the 20 %-of-equity sizing replaced), the default 2010-01-01 .. 2026-12-31 UTC backtest window, market orders at the next open, commission / slippage off.
Swing direction from the bars of the latest 30-bar highest high / lowest low, EMA(200) side, the 20-bar range over 0.8 ATR(20) chop filter, first-bar-of-run triggers inside the backtest window, structure-flip exits, and the 8 ATR(14) catastrophe stop frozen at entry (exit order re-issued every bar) are restated bar by bar.
Uses the quantity-aware bracket reference (indep.simulate_brackets). Variants: long only; both sides with a 12-bar swing and a 3 ATR backstop."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_ema, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "Eq4kPrrJ"
QTY = 10.0


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sw = p["sw"]
    t = df["time"].to_numpy()
    t0, t1 = int(pd.Timestamp("2010-01-01", tz="UTC").timestamp() * 1000), int(pd.Timestamp("2026-12-31 23:59", tz="UTC").timestamp() * 1000)
    ema = np_ema(c, 200)
    atr_b, atr_c = np_atr(h, l, c, 14), np_atr(h, l, c, 20)
    hh20 = np.array([h[i - 19:i + 1].max() if i >= 19 else np.nan for i in range(n)])
    ll20 = np.array([l[i - 19:i + 1].min() if i >= 19 else np.nan for i in range(n)])
    S = dict(phL=0, plL=0, lc=False, sc=False, bl=np.nan, bs=np.nan)

    def orders(i, info):
        out = []
        pos = info["pos"]
        if i >= sw - 1:
            if h[i] == h[i - sw + 1:i + 1].max():
                S["phL"] = i
            if l[i] == l[i - sw + 1:i + 1].min():
                S["plL"] = i
        d = 1 if S["phL"] > S["plL"] else -1
        with np.errstate(invalid="ignore"):
            rok = bool((hh20[i] - ll20[i]) > atr_c[i] * 0.8) and t0 <= t[i] <= t1
            lc = bool(d == 1 and c[i] > ema[i] and rok)
            sc = bool(p["short"] and d == -1 and c[i] < ema[i] and rok)
        lt, st = lc and not S["lc"], sc and not S["sc"]
        S["lc"], S["sc"] = lc, sc
        if lt and pos <= 0:
            S["bl"] = c[i] - atr_b[i] * p["mult"]
            out.append(("entry", "Long", 1, QTY))
        if st and pos >= 0:
            S["bs"] = c[i] + atr_b[i] * p["mult"]
            out.append(("entry", "Short", -1, QTY))
        if d == -1 and pos > 0:
            out.append(("close", "Long"))
        if d == 1 and pos < 0:
            out.append(("close", "Short"))
        nn = lambda x: None if np.isnan(x) else float(x)
        if pos > 0:
            out.append(("exit", "Long Backstop", "Long", None, nn(S["bl"]), None))
        if pos < 0:
            out.append(("exit", "Short Backstop", "Short", None, nn(S["bs"]), None))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=0.01, qty_step=1e-9)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


def check():
    df = bars(6000, seed=5, freq="B")
    df["time"] = df["time"] + int(14.5 * 3600 * 1000)
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.6
    msgs, allok = [], True
    cases = (({}, dict(sw=30, short=False, mult=8.0)),
             ({"Allow Short Entries?": True, "Swing Period": 12, "Backstop Distance (x ATR)": 3.0}, dict(sw=12, short=True, mult=3.0)))
    for params, ov in cases:
        ok, m = one(df, params, ov)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
