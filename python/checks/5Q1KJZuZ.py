"""Independent check — XAUUSD M5 Hybrid EMA 9/15 (5Q1KJZuZ): 5-minute bars (24 h synthetic, price scaled into the 2000s) on a crypto-style symbol (UTC 15-minute periods), market orders at the next open, fixed quantity 10 on the pinelib side (the original sizes 10 % of equity), commission / slippage / margin off.
Signal: EMA fast over slow on the chart and on the 15-minute period closes (lookahead off), a rejection candle (wick over 1.5 x body, closing with the trend). The entry issues two exit orders from the signal close: 50 % at close +/- TP1, and the runner (the other 50 %) with a take-profit at close +/- TP2, a stop at slow EMA - buffer (fast EMA + buffer for shorts)
and a trailing stop (activation 1.5 ticks of profit, offset 1 tick). Later signals while a trade is open re-issue the exit orders at the new levels (the entry itself is ignored: no pyramiding). Uses the quantity-aware bracket reference (indep.simulate_brackets, trailing leg included), which also compares the closed quantities.
Variants: defaults; wider targets and buffer; tighter targets, shorter EMAs."""
import numpy as np

from indep import bars, compare_q, np_ema, np_periods, np_security_lookahead_off, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "5Q1KJZuZ"
QTY = 10.0


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    sym = SymbolInfo.make("BINANCE:XAUUSDT", "crypto", qty_step=1e-9)
    ef, es = np_ema(c, p["f"]), np_ema(c, p["s"])
    pid, last_of = np_periods(df, 15, start_minutes=0, tz="UTC")
    pc = c[last_of]
    hf = np_security_lookahead_off(np_ema(pc, p["f"]), pid, last_of)
    hs = np_security_lookahead_off(np_ema(pc, p["s"]), pid, last_of)

    def orders(i, info):
        out = []
        with np.errstate(invalid="ignore"):
            bull = ef[i] > es[i] and hf[i] > hs[i]
            bear = ef[i] < es[i] and hf[i] < hs[i]
            body = abs(c[i] - o[i])
            uw, lw = h[i] - max(c[i], o[i]), min(c[i], o[i]) - l[i]
            buy = bull and lw > body * 1.5 and c[i] > o[i]
            sell = bear and uw > body * 1.5 and c[i] < o[i]
        if buy:
            out += [("entry", "BUY", 1, QTY), ("exit", "TP1 BUY", "BUY", 50, None, c[i] + p["t1"]),
                    ("exit", "TP2 BUY", "BUY", None, es[i] - p["buf"], c[i] + p["t2"], 1.5, None, 1)]
        if sell:
            out += [("entry", "SELL", -1, QTY), ("exit", "TP1 SELL", "SELL", 50, None, c[i] - p["t1"]),
                    ("exit", "TP2 SELL", "SELL", None, ef[i] + p["buf"], c[i] - p["t2"], 1.5, None, 1)]
        return out

    ref = simulate_brackets(o, h, l, c, orders, tick=sym.mintick)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(f=9, s=15, t1=1.0, t2=5.0, buf=0.3)


def check():
    df = bars(30000, seed=71, freq="5min")
    base = df["close"].iloc[0]
    for k in ("open", "high", "low", "close"):
        df[k] = 2000 * (df[k] / base) ** 0.12
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Partial TP (≈10 pips)": 2.5, "Runner TP (≈50 pips)": 9.0, "SL Buffer": 1.0}, dict(t1=2.5, t2=9.0, buf=1.0)),
             ({"EMA 9": 5, "EMA 15": 10, "Partial TP (≈10 pips)": 0.6, "Runner TP (≈50 pips)": 3.0}, dict(f=5, s=10, t1=0.6, t2=3.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
