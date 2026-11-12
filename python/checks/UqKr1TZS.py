"""Independent check — REVERSAL CLEAN MTF (UqKr1TZS): 5-minute bars (24 h synthetic) on a US stock chart (15- and 60-minute periods counted from 09:30 New York), orders at the bar close (process_orders_on_close), commission / slippage / margin off, one unit.
15-minute pivot highs / lows (lookahead off: a period's value shows on its last 5-minute bar and the first two of the next) make zones (pivot +/- ATR15 x width); a zone is replaced by a new different pivot (the low side is also gated by the high-pivot bar having been set), tests are counted with a 6-bar cooldown; on the first 5-minute bar of a 15-minute bar a rejection of the previous 15-minute bar
(new 5-bar extreme with the right candle colour and back inside the zone, with enough tests) arms a short / long setup (expires after 3 x bars); on the 5-minute chart a close through the last micro swing with a large enough body in the right direction confirms it (EMA15 / H1 / session filters optional), one trade per setup, stop beyond the failure high / low or zone plus a buffer, target at R:R, optional time exit.
Uses the pending-order reference broker (simulate_ord, on_close). Variants: defaults; 2 micro swing, zone width 0.6, minimum tests 2, R:R 2, buffer 0.1; EMA + H1 filters on with session filter, time exit after 20 bars, pivot 3, max extension 1.0."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_periods, np_security_lookahead_off, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "UqKr1TZS"
MT = 0.01


def piv(x, ln, high):
    out = np.full(len(x), np.nan)
    for i in range(2 * ln, len(x)):
        w = x[i - 2 * ln:i + 1]
        ctr = w[ln]
        a, b = w[:ln], w[ln + 1:]
        if (high and (a < ctr).all() and (b <= ctr).all()) or ((not high) and (a > ctr).all() and (b >= ctr).all()):
            out[i] = ctr
    return out


def roll(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    insess = (mins >= 420) & (mins < 1080)
    pid, last_of = np_periods(df, 15)
    npd = pid[-1] + 1
    ho = np.array([h[pid == k].max() for k in range(npd)])
    lo = np.array([l[pid == k].min() for k in range(npd)])
    co = c[last_of]
    oo = np.array([o[pid == k][0] for k in range(npd)])
    atr15 = np_atr(ho, lo, co, 14)
    mp = lambda a: np_security_lookahead_off(a, pid, last_of)
    m15h, m15l, m15c, m15a = mp(ho), mp(lo), mp(co), mp(atr15)
    m15ph, m15pl = mp(piv(ho, p["p15"], True)), mp(piv(lo, p["p15"], False))
    m15e = mp(np_ema(co, 50))
    hi5 = np.r_[np.nan, roll(ho, 5, np.max)[:-1]]
    lo5 = np.r_[np.nan, roll(lo, 5, np.min)[:-1]]
    with np.errstate(invalid="ignore"):
        brej = mp(((ho >= hi5) & (co < oo)).astype(float))
        urej = mp(((lo <= lo5) & (co > oo)).astype(float))
    pid60, last60 = np_periods(df, 60)
    c60 = c[last60]
    h1c = np_security_lookahead_off(c60, pid60, last60)
    h1e = np_security_lookahead_off(np_ema(c60, 50), pid60, last60)
    atr5 = np_atr(h, l, c, 14)
    ph5, pl5 = piv(h, p["p5"], True), piv(l, p["p5"], False)
    S = dict(res=np.nan, sup=np.nan, rt=np.nan, rb=np.nan, st=np.nan, sb=np.nan, rtests=0, stests=0, lrt=None, lst=None, lpb=None,
             ss=False, ls=False, sss=None, lss=None, sres=np.nan, ssup=np.nan, sfh=np.nan, sfl=np.nan, m5h=np.nan, m5l=np.nan, traded=False, tsb=None)

    def orders(i, pos):
        out = []
        with np.errstate(invalid="ignore"):
            npH = (not np.isnan(m15ph[i])) and (S["lpb"] is None or m15ph[i] != S["res"])
            npL = (not np.isnan(m15pl[i])) and (S["lpb"] is None or m15pl[i] != S["sup"])
            if npH:
                S["res"] = m15ph[i]
                S["rt"], S["rb"] = S["res"] + m15a[i] * p["zw"], S["res"] - m15a[i] * p["zw"]
                S["rtests"], S["lrt"], S["lpb"] = 1, i, i
            if npL:
                S["sup"] = m15pl[i]
                S["st"], S["sb"] = S["sup"] + m15a[i] * p["zw"], S["sup"] - m15a[i] * p["zw"]
                S["stests"], S["lst"] = 1, i
            rtn = (not np.isnan(S["res"])) and h[i] >= S["rb"] and h[i] <= S["rt"] + m15a[i] * p["ext"] and i > (S["lrt"] if S["lrt"] is not None else -100000) + 6
            stn = (not np.isnan(S["sup"])) and l[i] <= S["st"] and l[i] >= S["sb"] - m15a[i] * p["ext"] and i > (S["lst"] if S["lst"] is not None else -100000) + 6
            if rtn:
                S["rtests"] += 1
                S["lrt"] = i
            if stn:
                S["stests"] += 1
                S["lst"] = i
            bsr = (not np.isnan(S["res"])) and S["rtests"] >= p["mt"] and m15c[i] < S["rt"] and brej[i] == 1.0
            usr = (not np.isnan(S["sup"])) and S["stests"] >= p["mt"] and m15c[i] > S["sb"] and urej[i] == 1.0
        if i > 0 and pid[i] != pid[i - 1]:
            if bsr:
                S["ss"], S["ls"], S["sss"], S["sres"], S["sfh"] = True, False, i, S["res"], m15h[i]
            if usr:
                S["ls"], S["ss"], S["lss"], S["ssup"], S["sfl"] = True, False, i, S["sup"], m15l[i]
        if S["ss"] and i - (S["sss"] if S["sss"] is not None else 0) > p["sbars"] * 3:
            S["ss"] = False
        if S["ls"] and i - (S["lss"] if S["lss"] is not None else 0) > p["sbars"] * 3:
            S["ls"] = False
        with np.errstate(invalid="ignore"):
            sok = (not p["sess"]) or bool(insess[i])
            sf = bool(sok and ((not p["ema"]) or m15c[i] < m15e[i]) and ((not p["htf"]) or h1c[i] < h1e[i]))
            lf = bool(sok and ((not p["ema"]) or m15c[i] > m15e[i]) and ((not p["htf"]) or h1c[i] > h1e[i]))
            if not np.isnan(ph5[i]):
                S["m5h"] = ph5[i]
            if not np.isnan(pl5[i]):
                S["m5l"] = pl5[i]
            body = abs(c[i] - o[i]) >= atr5[i] * 0.12
            bc = c[i] < o[i] and body
            uc = c[i] > o[i] and body
            sc = bool(S["ss"] and sf and not np.isnan(S["m5l"]) and c[i] < S["m5l"] and bc)
            lc = bool(S["ls"] and lf and not np.isnan(S["m5h"]) and c[i] > S["m5h"] and uc)
        if not S["ss"] and not S["ls"]:
            S["traded"] = False
        with np.errstate(invalid="ignore"):
            if sc and not S["traded"] and pos == 0:
                sl = max(S["sfh"], S["sres"]) + atr5[i] * p["buf"] if not (np.isnan(S["sfh"]) or np.isnan(S["sres"])) else np.nan
                risk = sl - c[i]
                if risk > MT:
                    S["tsb"], S["traded"], S["ss"] = i, True, False
                    out.append(("entry", "SHORT", -1, None, None))
                    out.append(("exit", "SHORT EXIT", "SHORT", sl, c[i] - risk * p["rr"]))
            if lc and not S["traded"] and pos == 0:
                sl = min(S["sfl"], S["ssup"]) - atr5[i] * p["buf"] if not (np.isnan(S["sfl"]) or np.isnan(S["ssup"])) else np.nan
                risk = c[i] - sl
                if risk > MT:
                    S["tsb"], S["traded"], S["ls"] = i, True, False
                    out.append(("entry", "LONG", 1, None, None))
                    out.append(("exit", "LONG EXIT", "LONG", sl, c[i] + risk * p["rr"]))
        if p["tb"] > 0 and pos != 0 and S["tsb"] is not None and i - S["tsb"] >= p["tb"]:
            out.append(("close", "LONG" if pos > 0 else "SHORT"))
        return out

    ref = simulate_ord(o, h, l, c, orders, on_close=True)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(p15=4, p5=2, zw=0.35, ext=0.55, mt=2, sbars=16, rr=3.0, buf=0.25, ema=False, htf=False, sess=False, tb=0)


def check():
    df = bars(40000, seed=88, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Micro swing M5": 3, "Ampiezza zona x ATR": 0.6, "Risk / Reward": 2.0, "Buffer SL x ATR M5": 0.1}, dict(p5=3, zw=0.6, rr=2.0, buf=0.1)),
             ({"Filtro EMA M15": True, "Filtro trend H1": True, "Filtro orario": True, "Uscita dopo N barre M5 (0=off)": 20, "Pivot M15": 3, "Massima estensione oltre zona x ATR": 1.0},
              dict(ema=True, htf=True, sess=True, tb=20, p15=3, ext=1.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
