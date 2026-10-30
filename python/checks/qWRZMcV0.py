"""Independent check — XAUUSD Quant SMC (qWRZMcV0, identical to yid8vrVZ): 5-minute bars (24 h synthetic, drift-free, price ~100) of a stock-style symbol (New York hours), risk-sized fractional quantities (equity mirrored: initial capital + closed P&L + open P&L, floored to 1e-9), market orders at the next open, commission / slippage off.
Daily and 4-hour closes vs their EMA(50) (lookahead off), the 15-minute 10-bar highest / lowest and close (lookahead off, chart-bar lag of one for the structure level), the weekday-reset structure break and impulse range, the 0.618 retracement, the daily / weekly P&L limits in percent of initial capital (weekly reset on the ISO week of the 09:30-shifted time), the 07-13 exchange-hour window, the one-trade-a-day rule and the entry with stop at the impulse origin and the extended target are restated bar by bar.
Uses the quantity-aware bracket reference (indep.simulate_brackets). Variants: 5-minute and 10-minute charts (qWRZMcV0 and yid8vrVZ)."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_cross_over, np_cross_under, np_ema, np_periods, np_security_lookahead_off, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "qWRZMcV0"


def rq(q, step=1e-9):
    n = q / step
    return np.floor(n + max(1e-9, abs(n) * 1e-12)) * step


def wfn(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


def htf_trend(df, minutes):
    c = df["close"].to_numpy()
    pid, last_of = np_periods(df, minutes)
    pc = pd.Series(c).groupby(pid).last().to_numpy()
    e = np_security_lookahead_off(np_ema(pc, 50), pid, last_of)
    cc = np_security_lookahead_off(pc, pid, last_of)
    with np.errstate(invalid="ignore"):
        return np.where(cc > e, 1, -1)


def one(df, tf, tv_id):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    loc = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    hour = loc.dt.hour.to_numpy()
    dow = loc.dt.dayofweek.to_numpy()
    iso = (loc.dt.tz_localize(None) - pd.Timedelta(minutes=570)).dt.isocalendar()
    wk = np.array([f"{int(y)}-{int(w)}" for y, w in zip(iso["year"], iso["week"])])
    td, tq = htf_trend(df, 1440), htf_trend(df, 240)
    pid, last_of = np_periods(df, 15)
    g = pd.DataFrame({"pid": pid, "h": h, "l": l, "c": c}).groupby("pid")
    h15 = np_security_lookahead_off(wfn(g["h"].max().to_numpy(), 10, np.max), pid, last_of)
    l15 = np_security_lookahead_off(wfn(g["l"].min().to_numpy(), 10, np.min), pid, last_of)
    c15 = np_security_lookahead_off(g["c"].last().to_numpy(), pid, last_of)
    h15p, l15p = np.r_[np.nan, h15[:-1]], np.r_[np.nan, l15[:-1]]
    xu15, xd15 = np_cross_over(c15, h15p), np_cross_under(c15, l15p)
    log: list = []
    S = dict(bos=False, fh=np.nan, fl=np.nan, dp=0.0, wp=0.0, tt=0, closed=0, prev_c=None, f_prev=np.nan)

    def orders(i, info):
        out = []
        eq = 10000.0 + sum(d * (xp - ep) * q for d, _, ep, _, xp, q in log) + sum(x["d"] * x["q"] * (c[i] - x["ep"]) for x in info["lots"])
        bull = td[i] == 1 and tq[i] == 1
        aligned = (td[i] == 1 and tq[i] == 1) or (td[i] == -1 and tq[i] == -1)
        dchg = i > 0 and dow[i] != dow[i - 1]
        if dchg:
            S["bos"] = False
        with np.errstate(invalid="ignore"):
            if bull and xu15[i]:
                S["bos"], S["fh"], S["fl"] = True, h15[i], l15[i]
            elif (not bull) and xd15[i]:
                S["bos"], S["fh"], S["fl"] = True, h15[i], l15[i]
            f618 = S["fh"] - (S["fh"] - S["fl"]) * 0.618 if bull else S["fl"] + (S["fh"] - S["fl"]) * 0.618
        if dchg:
            S["dp"], S["tt"] = 0.0, 0
        if i > 0 and wk[i] != wk[i - 1]:
            S["wp"] = 0.0
        if len(log) > S["closed"]:
            last = log[-1]
            pnl = last[0] * (last[4] - last[2]) * last[5] / 10000.0 * 100
            S["dp"] += pnl
            S["wp"] += pnl
        S["closed"] = len(log)
        can = S["dp"] > -1.0 and S["wp"] > -3.0 and S["wp"] < 3.0 and S["tt"] < 1
        insess = 7 <= hour[i] < 13
        fp = S["f_prev"]
        S["f_prev"] = f618
        with np.errstate(invalid="ignore"):
            cu = bool(i > 0 and l[i] < f618 and l[i - 1] >= fp)
            co = bool(i > 0 and h[i] > f618 and h[i - 1] <= fp)
            lc = bool(aligned and bull and S["bos"] and cu and insess and can)
            sc = bool(aligned and (not bull) and S["bos"] and co and insess and can)
        risk = eq * 0.01
        if lc:
            sl, tp = S["fl"], S["fh"] + (S["fh"] - S["fl"]) * 0.5
            out += [("entry", "Long", 1, float(rq(risk / abs(c[i] - sl)))), ("exit", "Exit Long", "Long", None, sl, tp)]
            S["bos"], S["tt"] = False, 1
        if sc:
            sl, tp = S["fh"], S["fl"] - (S["fh"] - S["fl"]) * 0.5
            out += [("entry", "Short", -1, float(rq(risk / abs(c[i] - sl)))), ("exit", "Exit Short", "Short", None, sl, tp)]
            S["bos"], S["tt"] = False, 1
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=0.01, qty_step=1e-9, log=log)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(tv_id, df, symbol=sym, tf=tf, strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


def make(seed, n, freq, pw=0.4):
    df = bars(n, seed=seed, freq=freq)
    lc = np.log(df["close"].to_numpy() / 100)
    det = lc - np.polyval(np.polyfit(np.arange(len(lc)), lc, 1), np.arange(len(lc)))
    rel = {k: df[k].to_numpy() / df["close"].to_numpy() for k in ("open", "high", "low", "close")}
    for k in rel:
        df[k] = 100 * np.exp(pw * det) * rel[k] ** pw
    return df


def check():
    msgs, allok = [], True
    for tv_id, seed, n, freq, tf in (("qWRZMcV0", 5, 60000, "5min", "5"), ("yid8vrVZ", 6, 40000, "10min", "10")):
        ok, m = one(make(seed, n, freq), tf, tv_id)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
