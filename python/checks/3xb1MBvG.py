"""Independent check — GOLD EDGE FUND v3 (3xb1MBvG): 5-minute bars (24 h synthetic, drift-free, price ~100) of a stock-style symbol, 10 shares per entry (the 1 %-of-equity sizing replaced), market orders at the next open, commission / slippage off.
London / New York hour windows (exchange time), the 15-minute close / EMA(50) / EMA(200) bias (lookahead off), the chart EMA(20) / EMA(50) trend, the sweep / fair-value-gap / order-block triggers with the RSI momentum gate, an entry on every signal (pyramiding 0: same-side repeats are ignored, opposite entries reverse), the ATR stop / R:R target, break-even and trailing exit orders (separate ids, re-issued every bar), the -3 % day drawdown close_all (the day-start equity is taken when the day of month changes; the first bar counts as a change), the 7-entries-a-day counter and the cancel_all after it are restated bar by bar.
Uses the quantity-aware bracket reference (indep.simulate_brackets with several exit orders per entry). Variants: defaults; 2 trades a day and 0.5 % daily loss."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_ema, np_periods, np_rsi, np_security_lookahead_off, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "3xb1MBvG"
QTY = 10.0


def wfn(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    loc = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    hour, dom = loc.dt.hour.to_numpy(), loc.dt.day.to_numpy()
    pid, last_of = np_periods(df, 15)
    pc = pd.Series(c).groupby(pid).last().to_numpy()
    hc = np_security_lookahead_off(pc, pid, last_of)
    h50 = np_security_lookahead_off(np_ema(pc, 50), pid, last_of)
    h200 = np_security_lookahead_off(np_ema(pc, 200), pid, last_of)
    e20, e50 = np_ema(c, 20), np_ema(c, 50)
    lh, ll = wfn(h, 10, np.max), wfn(l, 10, np.min)
    rsi, atr = np_rsi(c, 14), np_atr(h, l, c, 14)
    log: list = []
    S = dict(dse=np.nan, tt=0, prev_n=None)

    def orders(i, info):
        out = []
        pos, avg, nlots = info["pos"], info["avg"], info["n"]
        eq = 10000.0 + sum(d * (xp - ep) * q for d, _, ep, _, xp, q in log) + sum(x["d"] * x["q"] * (c[i] - x["ep"]) for x in info["lots"])
        h2, l2, h1, l1, o1, c1 = (h[i - 2], l[i - 2], h[i - 1], l[i - 1], o[i - 1], c[i - 1]) if i >= 2 else (np.nan,) * 6
        with np.errstate(invalid="ignore"):
            sess = (7 <= hour[i] <= 10) or (13 <= hour[i] <= 16)
            hb, hr = bool(hc[i] > h50[i] and h50[i] > h200[i]), bool(hc[i] < h50[i] and h50[i] < h200[i])
            tu, td = bool(c[i] > e20[i] and e20[i] > e50[i]), bool(c[i] < e20[i] and e20[i] < e50[i])
            bf, sf = l[i] > h2, h[i] < l2
            bob, sob = bool(c[i] > h1 and o1 > c1), bool(c[i] < l1 and o1 < c1)
            lh1, ll1 = (lh[i - 1], ll[i - 1]) if i else (np.nan, np.nan)
            swh, swl = bool(h[i] > lh1 and c[i] < lh[i]), bool(l[i] < ll1 and c[i] > ll[i])
            lc = bool(sess and hb and tu and (swl or bf or bob) and rsi[i] > 55)
            sc = bool(sess and hr and td and (swh or sf or sob) and rsi[i] < 45)
        a = atr[i]
        lsl, ssl = c[i] - a * p["risk"], c[i] + a * p["risk"]
        ltp, stp = c[i] + a * p["risk"] * 1.6, c[i] - a * p["risk"] * 1.6
        if lc:
            out.append(("entry", "BUY", 1, QTY))
        if sc:
            out.append(("entry", "SELL", -1, QTY))
        out.append(("exit", "EXIT BUY", "BUY", None, lsl, ltp))
        out.append(("exit", "EXIT SELL", "SELL", None, ssl, stp))
        if pos > 0 and c[i] > avg + a * 0.8:
            out.append(("exit", "BE BUY", "BUY", None, avg, None))
        if pos < 0 and c[i] < avg - a * 0.8:
            out.append(("exit", "BE SELL", "SELL", None, avg, None))
        if pos > 0:
            out.append(("exit", "TRAIL BUY", "BUY", None, c[i] - a, None))
        if pos < 0:
            out.append(("exit", "TRAIL SELL", "SELL", None, c[i] + a, None))
        day_changed = i == 0 or dom[i] != dom[i - 1]
        if day_changed:
            S["dse"] = eq
        dd = 100 * (eq - S["dse"]) / S["dse"]
        if dd <= -p["mdl"]:
            out.append(("close_all",))
        if day_changed:
            S["tt"] = 0
        if S["prev_n"] is not None and nlots > S["prev_n"]:
            S["tt"] += 1
        S["prev_n"] = nlots
        if not (S["tt"] < p["mt"]):
            out.append(("cancel_all",))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=0.01, qty_step=1e-9, log=log)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


def check():
    df = bars(40000, seed=5, freq="5min")
    lc = np.log(df["close"].to_numpy() / 100)
    det = lc - np.polyval(np.polyfit(np.arange(len(lc)), lc, 1), np.arange(len(lc)))
    rel = {k: df[k].to_numpy() / df["close"].to_numpy() for k in ("open", "high", "low", "close")}
    for k in rel:
        df[k] = 100 * np.exp(0.4 * det) * rel[k] ** 0.4
    msgs, allok = [], True
    cases = (({}, dict(risk=1.3, mdl=3.0, mt=7)),
             ({"Max Trades Per Day": 2, "Max Daily Loss %": 0.5}, dict(risk=1.3, mdl=0.5, mt=2)))
    for params, ov in cases:
        ok, m = one(df, params, ov)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
