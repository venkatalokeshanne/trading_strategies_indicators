"""Independent check — TMO Dual Timeframe Strategy (xm1plELH): 1-minute bars (24 h synthetic, compressed) on a US stock chart (periods are blocks of the timeframe counted from 09:30 New York per trading day), market orders at the next open. TMO per higher-timeframe bar: s = sum over the last length+1 opens of sign(close - open[k]); main = MA(MA(s, calc), smooth), signal = MA(main, smooth) with EMA / SMA / RMA choices; shown on chart bars with lookahead off (the value of a period appears on its last chart bar, the previous period's before). Long when the trend timeframe's main > 0 and the entry timeframe's main crosses above 0 (short mirrored); the opposite signal also closes; percent / pip stop and target from the average price are issued while the trade is open. Uses the pending-order reference broker (simulate_ord).
Variants: HTM 1hr / ETM 3m defaults; HTM 30m / ETM 5m with SMA / RMA types and pips; shorts only with tighter stops and another TMO length."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_periods, np_security_lookahead_off, np_sma, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "xm1plELH"


def ema_na(x, n):
    out = np.full(len(x), np.nan)
    idx = np.flatnonzero(~np.isnan(x))
    if len(idx) < n:
        return out
    s = idx[0] + n - 1
    out[s] = x[idx[0]:s + 1].mean()
    k = 2.0 / (n + 1)
    for i in range(s + 1, len(x)):
        out[i] = k * x[i] + (1 - k) * out[i - 1]
    return out


def rma_na(x, n):
    out = np.full(len(x), np.nan)
    idx = np.flatnonzero(~np.isnan(x))
    if len(idx) < n:
        return out
    s = idx[0] + n - 1
    out[s] = x[idx[0]:s + 1].mean()
    for i in range(s + 1, len(x)):
        out[i] = (x[i] + (n - 1) * out[i - 1]) / n
    return out


def ma(t, x, n):
    return {"EMA": ema_na, "SMA": np_sma, "RMA": rma_na}[t](x, n)


def tmo(o_p, c_p, p):
    s = np.zeros(len(c_p))
    for t in range(len(c_p)):
        acc = 0.0
        for k in range(p["len"] + 1):
            if t - k >= 0:
                acc += 1 if c_p[t] > o_p[t - k] else (-1 if c_p[t] < o_p[t - k] else 0)
        s[t] = acc
    m1 = ma(p["lt"], s, p["calc"])
    main = ma(p["ct"], m1, p["smooth"])
    sig = ma(p["st"], main, p["smooth"])
    return main, sig


def htf_series(df, minutes, p):
    o, c = df["open"].to_numpy(), df["close"].to_numpy()
    pid, last_of = np_periods(df, minutes)
    first_of = np.r_[True, pid[1:] != pid[:-1]]
    main, _ = tmo(o[first_of], c[last_of], p)
    return np_security_lookahead_off(main, pid, last_of)


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    tick = sym.mintick
    hm = htf_series(df, p["htm"], p)
    em = htf_series(df, p["etm"], p)
    em1 = np.r_[np.nan, em[:-1]]
    with np.errstate(invalid="ignore"):
        xu = (em > 0) & (em1 <= 0)
        xd = (em < 0) & (em1 >= 0)
        buy = (hm > 0) & xu
        sell = (hm < 0) & xd
    nn = lambda x: None if np.isnan(x) else x

    def dist(amount, unit, price):
        return price * amount / 100 if unit == "Percent" else amount * tick * p["pip"]

    def orders(i, pos, info):
        out = []
        if buy[i] and p["long"]:
            out.append(("entry", "Long", 1, None, None))
        if sell[i] and p["short"]:
            out.append(("entry", "Short", -1, None, None))
        if sell[i] and p["long"]:
            out.append(("close", "Long"))
        if buy[i] and p["short"]:
            out.append(("close", "Short"))
        if pos != 0 and (p["usesl"] or p["usetp"]):
            ep = info["ep"]
            sl = dist(p["sla"], p["slu"], ep)
            tp = dist(p["tpa"], p["tpu"], ep)
            if pos > 0:
                out.append(("exit", "Long Exit", "Long", ep - sl if p["usesl"] else None, ep + tp if p["usetp"] else None))
            else:
                out.append(("exit", "Short Exit", "Short", ep + sl if p["usesl"] else None, ep - tp if p["usetp"] else None))
        return out

    ref = simulate_ord(o, h, l, c, orders)
    start = 1.4e12
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="1", params={**params, "Start date": start},
                                   strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(htm=60, etm=3, len=14, calc=5, smooth=3, lt="EMA", ct="EMA", st="EMA", long=True, short=True, usesl=True, slu="Percent", sla=2.0, usetp=True, tpu="Percent", tpa=4.0, pip=10)


def check():
    df = bars(25000, seed=1234, freq="1min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.15
    msgs, allok = [], True
    cases = (({}, {}),
             ({"HTM - Higher Timeframe (trend)": "30m", "ETM - Entry Timeframe (trigger)": "5m", "Length MA type": "SMA", "Calc length MA type": "RMA", "Stop loss unit": "Pips",
               "Stop loss amount": 30.0, "Take profit unit": "Pips", "Take profit amount": 60.0},
              dict(htm=30, etm=5, lt="SMA", ct="RMA", slu="Pips", sla=30.0, tpu="Pips", tpa=60.0)),
             ({"Allow long trades": False, "Length": 9, "Stop loss amount": 1.0, "Use take profit": False, "Smooth length MA type": "SMA"},
              dict(long=False, len=9, sla=1.0, usetp=False, st="SMA")))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
