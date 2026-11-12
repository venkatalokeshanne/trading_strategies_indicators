"""Independent check — Xiznit Scalper (oPZA3pgr): 5-minute bars (24 h synthetic) on a US stock chart, hours in America/Chicago, market orders at the next open, margin / commission / slippage off, one unit.
Sessions Asia (19-24 CT), London (02-08), New York (08-15) with per-session entry caps reset at each session's first bar and a global cooldown; ER regime (|c - c[n]| / sum of |dc| over n bars, 0 when the path is not > 0) gates the four signals (EMA cross and Heikin Ashi + RSI need regime 2; session-VWAP deviation and price structure need >= 1);
the VWAP accumulator restarts at any session's first bar; optional filters: volume surge, hand-written ADX (Wilder RMA of DM and true range), 15-minute EMA of period closes (lookahead off), VWAP bias, ROC. ATR stop and R:R target are issued with the entry. Uses the pending-order reference broker (simulate_ord).
Variants: defaults (ER 0.3 / 0.15 so the EMA cross trades); VWAP Deviation with the volume + ADX filters; Heikin Ashi + RSI with HTF align + ROC; Price Structure (3 candles) with VWAP bias, cooldown 6, Asia off."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_ema, np_periods, np_rsi, np_security_lookahead_off, np_sma, np_tr, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "oPZA3pgr"


def rma_na(x, n):
    out = np.full(len(x), np.nan)
    ok = ~np.isnan(x)
    run = 0
    s = None
    for i in range(len(x)):
        run = run + 1 if ok[i] else 0
        if run == n:
            s = i
            break
    if s is None:
        return out
    out[s] = x[s - n + 1:s + 1].mean()
    a = 1.0 / n
    for i in range(s + 1, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    hr = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/Chicago").dt.hour.to_numpy()
    in_asia = p["asia"] & ((hr >= 19) | (hr < 0))
    in_lon = (hr >= 2) & (hr < 8)
    in_ny = (hr >= 8) & (hr < 15)
    ps = np.r_[np.nan, c[:-1]]
    step = np.abs(c - ps)
    er = np.zeros(n)
    for i in range(n):
        if i >= p["erl"]:
            path = step[i - p["erl"] + 1:i + 1].sum()
            er[i] = abs(c[i] - c[i - p["erl"]]) / path if path > 0 else 0.0
    regime = np.where(er >= p["etm"], 2, np.where(er >= p["erm"], 1, 0))
    atr = np_atr(h, l, c, 14)
    up = h - np.r_[np.nan, h[:-1]]
    dn = np.r_[np.nan, l[:-1]] - l
    with np.errstate(invalid="ignore"):
        dmp = np.where((up > dn) & (up > 0), up, 0.0)
        dmm = np.where((dn > up) & (dn > 0), dn, 0.0)
    atr_adx = rma_na(np_tr(h, l, c, True), 14)
    with np.errstate(invalid="ignore", divide="ignore"):
        dip = 100 * rma_na(dmp, 14) / atr_adx
        dim = 100 * rma_na(dmm, 14) / atr_adx
        dx = np.abs(dip - dim) / (dip + dim) * 100
    adx = rma_na(dx, 14)
    pid, last_of = np_periods(df, 15)
    htf = np_security_lookahead_off(np_ema(c[last_of], 50), pid, last_of)
    cp9 = np.r_[np.full(9, np.nan), c[:-9]]
    with np.errstate(invalid="ignore", divide="ignore"):
        roc = (c - cp9) / cp9 * 100
    ef, es = np_ema(c, 9), np_ema(c, 21)
    xo, xu = np_cross_over(ef, es), np_cross_under(ef, es)
    hac = (o + h + l + c) / 4
    hao = np.empty(n)
    for i in range(n):
        hao[i] = (o[i] + c[i]) / 2 if i == 0 else (hao[i - 1] + hac[i - 1]) / 2
    rsi = np_rsi(c, 14)
    vavg = np_sma(v, 20)
    hl3 = (h + l + c) / 3.0
    S = dict(pa=False, pl=False, pn=False, ta=0, tl=0, tn=0, bse=9999, vn=0.0, vd=0.0)

    def orders(i, pos, info):
        out = []
        ia, il, iny = bool(in_asia[i]), bool(in_lon[i]), bool(in_ny[i])
        any_s = ia or il or iny
        ao, lo_, no = ia and not S["pa"], il and not S["pl"], iny and not S["pn"]
        if ao:
            S["ta"] = 0
        if lo_:
            S["tl"] = 0
        if no:
            S["tn"] = 0
        cnt = S["ta"] if ia else (S["tl"] if il else (S["tn"] if iny else 999))
        mx = p["amax"] if ia else (5 if il else (5 if iny else 0))
        trades_ok = any_s and cnt < mx
        S["bse"] += 1
        cool_ok = S["bse"] >= p["cool"]
        if ao or lo_ or no:
            S["vn"] = S["vd"] = 0.0
        S["vn"] += hl3[i] * v[i]
        S["vd"] += v[i]
        vw = S["vn"] / S["vd"] if S["vd"] > 0 else hl3[i]
        with np.errstate(invalid="ignore", divide="ignore"):
            f_vol = (not p["fv"]) or v[i] > vavg[i] * 1.5
            f_adx = (not p["fa"]) or adx[i] >= 20
            f_hl = (not p["fh"]) or c[i] > htf[i]
            f_hs = (not p["fh"]) or c[i] < htf[i]
            vb = p["fb"] and p["mode"] != "VWAP Deviation"
            f_bl = (not vb) or c[i] > vw
            f_bs = (not vb) or c[i] < vw
            f_rl = (not p["fr"]) or roc[i] > 0
            f_rs = (not p["fr"]) or roc[i] < 0
            fl, fs = bool(f_vol and f_adx and f_hl and f_bl and f_rl), bool(f_vol and f_adx and f_hs and f_bs and f_rs)
            devp = (c[i] - vw) / vw
            ha_b = i > 0 and hac[i] > hao[i] and hac[i - 1] > hao[i - 1]
            ha_s = i > 0 and hac[i] < hao[i] and hac[i - 1] < hao[i - 1]
            if p["sb"] == 2:
                sl_ = i > 0 and h[i] > h[i - 1] and l[i] > l[i - 1]
                ss_ = i > 0 and h[i] < h[i - 1] and l[i] < l[i - 1]
            else:
                sl_ = i > 1 and h[i] > h[i - 1] > h[i - 2] and l[i] > l[i - 1] > l[i - 2]
                ss_ = i > 1 and h[i] < h[i - 1] < h[i - 2] and l[i] < l[i - 1] < l[i - 2]
            m = p["mode"]
            r = regime[i]
            sig_l = (m == "EMA Cross" and r == 2 and xo[i]) or (m == "VWAP Deviation" and r >= 1 and devp < -0.0015) or \
                    (m == "Heikin Ashi + RSI" and r == 2 and ha_b and rsi[i] > 55) or (m == "Price Structure" and r >= 1 and sl_)
            sig_s = (m == "EMA Cross" and r == 2 and xu[i]) or (m == "VWAP Deviation" and r >= 1 and devp > 0.0015) or \
                    (m == "Heikin Ashi + RSI" and r == 2 and ha_s and rsi[i] < 45) or (m == "Price Structure" and r >= 1 and ss_)
        flat = pos == 0
        cel = bool(sig_l and flat and trades_ok and cool_ok and any_s and fl)
        ces = bool(sig_s and flat and trades_ok and cool_ok and any_s and fs)
        for ok_, d, nm in ((cel, 1, "Long"), (ces, -1, "Short")):
            if ok_:
                out.append(("entry", nm, d, None, None))
                out.append(("exit", nm + " Exit", nm, c[i] - d * atr[i] * 1.2, c[i] + d * atr[i] * 1.2 * 1.5))
                S["bse"] = 0
                if ia:
                    S["ta"] += 1
                elif il:
                    S["tl"] += 1
                elif iny:
                    S["tn"] += 1
        S["pa"], S["pl"], S["pn"] = ia, il, iny
        return out

    ref = simulate_ord(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(mode="EMA Cross", erl=10, etm=0.6, erm=0.3, asia=True, amax=5, cool=3, fv=False, fa=False, fh=False, fb=False, fr=False, sb=2)


def check():
    df = bars(40000, seed=15, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.1
    msgs, allok = [], True
    cases = (({"Trending Threshold ≥": 0.3, "Mild Ranging Threshold ≥": 0.15}, dict(etm=0.3, erm=0.15)),
             ({"Entry Signal Mode": "VWAP Deviation", "Volume Surge": True, "ADX Strength": True, "Trending Threshold ≥": 0.4, "Mild Ranging Threshold ≥": 0.1},
              dict(mode="VWAP Deviation", fv=True, fa=True, etm=0.4, erm=0.1)),
             ({"Entry Signal Mode": "Heikin Ashi + RSI", "HTF Trend Align": True, "ROC Momentum": True, "Trending Threshold ≥": 0.3, "Mild Ranging Threshold ≥": 0.1},
              dict(mode="Heikin Ashi + RSI", fh=True, fr=True, etm=0.3, erm=0.1)),
             ({"Entry Signal Mode": "Price Structure", "Structure Lookback Candles (2–3)": 3, "VWAP Bias": True, "Cooldown Bars Between Entries": 6, "Asia Session": False, "Mild Ranging Threshold ≥": 0.1},
              dict(mode="Price Structure", sb=3, fb=True, cool=6, asia=False, erm=0.1)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
