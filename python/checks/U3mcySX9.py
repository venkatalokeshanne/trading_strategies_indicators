"""Independent check — Technical Summary + Crowd Consensus, Triggon Lite (U3mcySX9): 15-minute bars (24 h synthetic) on a US stock chart (daily periods counted from 09:30 New York), market orders at the next open, margin / commission / slippage off, one unit (a fixed quantity of 1 replaces the 100%-of-equity sizing, which a long losing short run can bankrupt).
Ten oscillator votes (RSI, Stochastic %K/%D, CCI, MACD, AO, Momentum 10, Williams %R, Stoch RSI, Ultimate, Bull-Bear power) and twelve moving-average votes (EMA / SMA 10-200, VWMA 20, HMA 9 with half = 5, sqrt = 3) written from their formulas; a value that is missing (warm-up, zero range) votes neutral, as every comparison with it is false.
consensus = max(buy, sell) / votes; tier 0 below the neutral threshold; a daily phase (reset on the first bar of each new day) flips when a non-neutral bias opposes it; the confirmed flip with the signal threshold (>= or <=) and the whole candle on the right side of the EMA enters in the new direction (reversing). Uses the reference broker (simulate).
Variants: defaults; extreme 60 / signal 50 / EMA 20 on HL2; 'At Most' 58 without the EMA filter and RSI + VWMA votes off; EMA 100 on OHLC4, neutral threshold 30, extreme 55, signal 60."""
import numpy as np

from indep import bars, compare, np_cci, np_periods, np_rsi, np_sma, np_wma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "U3mcySX9"


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


def roll(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        out[i] = fn(w) if not np.isnan(w).all() else np.nan
    return out


def wsum(x, n):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        if not np.isnan(w).any():
            out[i] = w.sum()
    return out


def sel(conds, vals):
    return np.select(conds, vals, 0).astype(int)


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    with np.errstate(invalid="ignore", divide="ignore"):
        rsi = np_rsi(c, 14)
        votes = {}
        votes["rsi"] = sel([rsi >= 70, rsi <= 30, rsi > 50, rsi < 50], [-1, 1, 1, -1])
        hh, ll = roll(h, 14, np.max), roll(l, 14, np.min)
        stoch = 100 * (c - ll) / (hh - ll)
        k = np_sma(stoch, 3)
        d = np_sma(k, 3)
        votes["stoch"] = sel([k >= 80, k <= 20, k > d, k < d], [-1, 1, 1, -1])
        ci = np_cci((h + l + c) / 3.0, 20)
        votes["cci"] = sel([ci >= 100, ci <= -100, ci > 0, ci < 0], [1, -1, 1, -1])
        ml = ema_na(c, 12) - ema_na(c, 26)
        ms = ema_na(ml, 9)
        votes["macd"] = sel([ml > ms, ml < ms], [1, -1])
        mid = (h + l) / 2.0
        ao = np_sma(mid, 5) - np_sma(mid, 34)
        votes["ao"] = sel([ao > 0, ao < 0], [1, -1])
        mom = c - np.r_[np.full(10, np.nan), c[:-10]]
        votes["mom"] = sel([mom > 0, mom < 0], [1, -1])
        rng = hh - ll
        wr = np.where(rng != 0, -100.0 * (hh - c) / rng, -50.0)
        votes["wr"] = sel([wr >= -20, wr <= -80, wr > -50, wr < -50], [-1, 1, 1, -1])
        lo_r, hi_r = roll(rsi, 14, np.nanmin), roll(rsi, 14, np.nanmax)
        dr = hi_r - lo_r
        raw = np.where(dr != 0, (rsi - lo_r) / dr, 0.5)
        sk = np_sma(raw, 3)
        sd = np_sma(sk, 3)
        votes["srsi"] = sel([sk >= 0.8, sk <= 0.2, sk > sd, sk < sd], [-1, 1, 1, -1])
        pc = np.r_[np.nan, c[:-1]]
        bp = c - np.minimum(l, pc)
        trv = np.maximum(h, pc) - np.minimum(l, pc)
        av = []
        for ln in (7, 14, 28):
            a, b = wsum(bp, ln), wsum(trv, ln)
            av.append(np.where(b != 0, a / b, 0.5))
        uo = 100.0 * (4.0 * av[0] + 2.0 * av[1] + av[2]) / 7.0
        votes["uo"] = sel([uo >= 70, uo <= 30, uo > 50, uo < 50], [-1, 1, 1, -1])
        bbp = c - ema_na(c, 13)
        votes["bbp"] = sel([bbp > 0, bbp < 0], [1, -1])
        for ln in (10, 20, 50, 100, 200):
            e, s = ema_na(c, ln), np_sma(c, ln)
            votes[f"ema{ln}"] = sel([c > e, c < e], [1, -1])
            votes[f"sma{ln}"] = sel([c > s, c < s], [1, -1])
        vw = np_sma(c * v, 20) / np_sma(v, 20)
        votes["vwma"] = sel([c > vw, c < vw], [1, -1])
        hm = np_wma(2.0 * np_wma(c, 5) - np_wma(c, 9), 3)
        votes["hma"] = sel([c > hm, c < hm], [1, -1])
    on = [kk for kk in votes if kk not in p["off"]]
    buy = sum((votes[kk] == 1).astype(int) for kk in on)
    sell = sum((votes[kk] == -1).astype(int) for kk in on)
    neut = sum((votes[kk] == 0).astype(int) for kk in on)
    cons = np.maximum(buy, sell) / np.maximum(buy + sell + neut, 1) * 100.0
    dom = buy >= sell
    tier = np.where(cons < p["neut"], 0, np.where(cons < p["ext"], 1, np.where(cons < p["very"], 2, 3)))
    pid, _ = np_periods(df, 1440)
    srcs = {"Close": c, "Open": o, "High": h, "Low": l, "HL2": (h + l) / 2, "HLC3": (h + l + c) / 3, "OHLC4": (o + h + l + c) / 4}
    em = ema_na(srcs[p["src"]], p["el"])
    S = dict(phase=0)

    def orders(i, pos):
        newday = i == 0 or pid[i] != pid[i - 1]
        raw_b = 0 if tier[i] == 0 else (1 if dom[i] else -1)
        change = False
        if newday:
            S["phase"] = 0
        if raw_b != 0:
            if S["phase"] == 0:
                S["phase"] = raw_b
            elif S["phase"] != raw_b:
                S["phase"] = raw_b
                change = True
        ok = cons[i] >= p["thr"] if p["mode"] == "ge" else cons[i] <= p["thr"]
        if not p["ema"]:
            eok = True
        elif S["phase"] == 1:
            eok = l[i] > em[i]
        elif S["phase"] == -1:
            eok = h[i] < em[i]
        else:
            eok = False
        if change and ok and eok:
            return [("entry", S["phase"])]
        return []

    ref = simulate(o, h, l, c, orders)
    ok_, d_ = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0, "default_qty_type": "fixed", "default_qty_value": 1}), ref)
    return ok_ and len(ref) > 8, f"{d_} (got {len(ref)})"


BASE = dict(off=(), neut=45, ext=70, very=85, thr=65, mode="ge", ema=True, el=50, src="Close")


def check():
    df = bars(30000, seed=9, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Extreme Threshold %": 60, "Threshold %": 50, "EMA Length": 20, "EMA Source": "HL2"}, dict(ext=60, thr=50, el=20, src="HL2")),
             ({"Required Consensus": "At Most (≤)", "Threshold %": 58, "Require EMA Alignment": False, "RSI (14)": False, "VWMA 20": False}, dict(mode="le", thr=58, ema=False, off=("rsi", "vwma"))),
             ({"EMA Length": 100, "EMA Source": "OHLC4", "Neutral Below %": 30, "Extreme Threshold %": 55, "Threshold %": 60}, dict(el=100, src="OHLC4", neut=30, ext=55, thr=60)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
