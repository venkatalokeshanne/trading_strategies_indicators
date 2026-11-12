"""Independent check — 1H Swings -> 1H Mitigation -> 5m Displacement -> 5m FVG Entry (6xRw0a6S): 5-minute bars (24 h synthetic, drift-free, price ~100) of a stock-style symbol, 1 contract per entry, orders at the bar's close (process_orders_on_close), commission / slippage off.
Hourly 3-candle swings and the stateful mitigation function evaluated on the aggregated 60-minute bars (lookahead off, with the hourly bar time), the new-mitigation stamp, the displacement and fair-value-gap memory, the one-trade-per-mitigation rule, the entry on the bar after the setup with the stop beyond the hourly wick and the 2 R target are restated bar by bar.
Uses the quantity-aware bracket reference (indep.simulate_brackets, on_close). Variants: defaults; no displacement requirement, 1.5 R, 2-tick buffer 0."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_periods, np_security_lookahead_off, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "6xRw0a6S"
TICK = 0.01


def pivots(x, left, right, high):
    out = np.full(len(x), False)
    for i in range(left + right, len(x)):
        w = x[i - left - right:i + 1]
        ctr = w[left]
        a, b = w[:left], w[left + 1:]
        out[i] = ((a < ctr).all() and (b <= ctr).all()) if high else ((a > ctr).all() and (b >= ctr).all())
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    t = df["time"].to_numpy().astype(float)
    pid, last_of = np_periods(df, 60)
    g = pd.DataFrame({"pid": pid, "h": h, "l": l, "c": c, "t": t}).groupby("pid")
    hh, hl, hc, ht = g["h"].max().to_numpy(), g["l"].min().to_numpy(), g["c"].last().to_numpy(), g["t"].first().to_numpy()
    m = len(hh)
    php, plp = pivots(hh, 1, 1, True), pivots(hl, 1, 1, False)
    d_arr, shi_arr, slo_arr = np.zeros(m), np.full(m, np.nan), np.full(m, np.nan)
    lsh = lsl = np.nan
    for j in range(m):
        if php[j]:
            lsh = hh[j - 1]
        if plp[j]:
            lsl = hl[j - 1]
        bear = (not np.isnan(lsh)) and hh[j] > lsh and hc[j] < lsh
        bull = (not np.isnan(lsl)) and hl[j] < lsl and hc[j] > lsl
        d_arr[j] = 1 if bull else -1 if bear else 0
        shi_arr[j] = hh[j] if bear else np.nan
        slo_arr[j] = hl[j] if bull else np.nan
    mp = lambda a: np_security_lookahead_off(a, pid, last_of)
    hd, hsh, hsl, htm = mp(d_arr), mp(shi_arr), mp(slo_arr), mp(ht)
    atr = np_atr(h, l, c, 14)
    S = dict(adir=0, asl=np.nan, mbar=None, stamp=np.nan, ftop=np.nan, fbot=np.nan, fdir=0, disp=False, traded=False, ls_prev=False, ss_prev=False)

    def orders(i, info):
        out = []
        pos = info["pos"]
        d = hd[i]
        nm = bool(d != 0 and (np.isnan(S["stamp"]) or htm[i] != S["stamp"])) if not np.isnan(d) else False
        if nm:
            S["adir"], S["mbar"], S["stamp"] = int(d), i, htm[i]
            if S["adir"] == -1 and not np.isnan(hsh[i]):
                S["asl"] = hsh[i] + p["buf"] * TICK
            if S["adir"] == 1 and not np.isnan(hsl[i]):
                S["asl"] = hsl[i] - p["buf"] * TICK
        body = abs(c[i] - o[i])
        with np.errstate(invalid="ignore"):
            bu = c[i] > o[i] and body >= atr[i] * 0.8
            be = c[i] < o[i] and body >= atr[i] * 0.8
        dispok = True if not p["disp"] else (bu if S["adir"] == 1 else be if S["adir"] == -1 else False)
        h2, l2 = (h[i - 2], l[i - 2]) if i >= 2 else (np.nan, np.nan)
        aft = S["mbar"] is not None and i > S["mbar"]
        if nm:
            S["disp"], S["ftop"], S["fbot"], S["fdir"] = False, np.nan, np.nan, 0
        if aft and dispok:
            S["disp"] = True
        with np.errstate(invalid="ignore"):
            if aft and S["disp"]:
                if S["adir"] == 1 and l[i] > h2:
                    S["ftop"], S["fbot"], S["fdir"] = l[i], h2, 1
                if S["adir"] == -1 and h[i] < l2:
                    S["ftop"], S["fbot"], S["fdir"] = l2, h[i], -1
            infvg = S["fdir"] != 0 and (not np.isnan(S["ftop"])) and (not np.isnan(S["fbot"])) and l[i] <= S["ftop"] and h[i] >= S["fbot"]
        if nm:
            S["traded"] = False
        can = pos == 0 and (not S["traded"])
        ls_, ss_ = bool(can and S["fdir"] == 1 and infvg), bool(can and S["fdir"] == -1 and infvg)
        if S["ls_prev"]:
            risk = o[i] - S["asl"]
            if risk > TICK:
                out += [("entry", "L", 1, 1.0), ("exit", "L-TP/SL", "L", None, S["asl"], o[i] + risk * p["rr"])]
                S["traded"] = True
        if S["ss_prev"]:
            risk = S["asl"] - o[i]
            if risk > TICK:
                out += [("entry", "S", -1, 1.0), ("exit", "S-TP/SL", "S", None, S["asl"], o[i] - risk * p["rr"])]
                S["traded"] = True
        S["ls_prev"], S["ss_prev"] = ls_, ss_
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, on_close=True, tick=TICK, qty_step=1e-9)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, dd = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params,
                                      strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{dd} (got {len(ref)})"


def check():
    df = bars(60000, seed=5, freq="5min")
    lc = np.log(df["close"].to_numpy() / 100)
    det = lc - np.polyval(np.polyfit(np.arange(len(lc)), lc, 1), np.arange(len(lc)))
    rel = {k: df[k].to_numpy() / df["close"].to_numpy() for k in ("open", "high", "low", "close")}
    for k in rel:
        df[k] = 100 * np.exp(0.3 * det) * rel[k] ** 0.3
    msgs, allok = [], True
    cases = (({}, dict(buf=2, rr=2.0, disp=True)),
             ({"Require displacement AFTER mitigation": False, "Risk:Reward (TP = RR * Risk)": 1.5, "SL buffer (ticks) beyond 1H wick": 0}, dict(buf=0, rr=1.5, disp=False)))
    for params, ov in cases:
        ok, m = one(df, params, ov)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
