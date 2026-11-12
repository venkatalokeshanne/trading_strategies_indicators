"""Independent check — Concordance Execution Model [JOAT] (zpKLbjA0): 15-minute bars (24 h synthetic) on a US stock chart (higher-timeframe periods counted from 09:30 New York), market orders at the next open, commission / slippage / margin off.
Long / short score from: structure break (latest pivot +/- 0.05 ATR, level cleared once used), bias-HTF close[1] vs EMA50[1], the vote of four ALMA-band states (15 / 60 / 240 / D periods, each on the previous period's close; ALMA(6, 0.85, 4) with a trailing band of stdev(4), lookahead off),
the alpha-beta-gamma kinetic filter, R-squared of the linreg window with its 5-bar slope, delta pressure (EMA7 of the volume-weighted close position, OBV vs its SMA, close vs the session VWAP, relative volume) and the EMA50/200 stack; an entry needs score >= 72, delta beyond its gate, relative volume and the cooldown (reversing allowed).
Exits: stop (ATR, ratcheted by the ATR trail) and ATR target re-issued each bar from the average entry price (position open at script time), a time stop and a structure / opposing-score invalidation close. Uses the pending-order reference broker (simulate_ord).
Variants: defaults; 60-minute bias, pivot 3, confidence 0.30, delta gate 0, relative volume 0.8, cooldown 3, stop 1.2 / target 2.0, time stop 20; ALMA 10 / dev 6 / factor 0.5, trail 1.0 with the trail off, regression window 40."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, np_periods, np_security_lookahead_off, np_sma, np_vwap, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "zpKLbjA0"
MT = 0.01


def alma(x, n, off, sig):
    m, s = off * (n - 1), n / sig
    w = np.exp(-((np.arange(n) - m) ** 2) / (2 * s * s))
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = (x[i - n + 1:i + 1] * w).sum() / w.sum()
    return out


def stdev0(x, n):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = x[i - n + 1:i + 1].std()
    return out


def var0(x, n):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = x[i - n + 1:i + 1].var()
    return out


def linreg(x, n):
    out = np.full(len(x), np.nan)
    xs = np.arange(n, dtype=float)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        if np.isnan(w).any():
            continue
        s, b = np.polyfit(xs, w, 1)
        out[i] = b + s * (n - 1)
    return out


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


def band_dir(df, minutes, alen, dlen, fac):
    pid, last_of = np_periods(df, minutes)
    pc = df["close"].to_numpy()[last_of]
    src = np.r_[np.nan, pc[:-1]]
    a = alma(src, alen, 0.85, 4.0)
    sd = stdev0(src, dlen)
    m = len(src)
    d = np.zeros(m)
    up_prev = lo_prev = np.nan
    s_prev = np.nan
    dr = 0
    for k in range(m):
        u, lo = a[k] + fac * sd[k], a[k] - fac * sd[k]
        pu = up_prev if not np.isnan(up_prev) else u
        pl_ = lo_prev if not np.isnan(lo_prev) else lo
        u = u if (u < pu or s_prev > pu) else pu
        lo = lo if (lo > pl_ or s_prev < pl_) else pl_
        if src[k] > u:
            dr = 1
        elif src[k] < lo:
            dr = -1
        d[k] = dr
        up_prev, lo_prev, s_prev = u, lo, src[k]
    return np_security_lookahead_off(d, pid, last_of)


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    atr = np_atr(h, l, c, 14)
    e50, e200 = ema_na(c, 50), ema_na(c, 200)
    pid, last_of = np_periods(df, p["htf"])
    pcl = c[last_of]
    hc = np_security_lookahead_off(np.r_[np.nan, pcl[:-1]], pid, last_of)
    he = np_security_lookahead_off(np.r_[np.nan, ema_na(pcl, 50)[:-1]], pid, last_of)
    vote = sum(band_dir(df, mm, p["al"], p["dl"], p["af"]) for mm in (15, 60, 240, 1440))
    ph = np.full(n, np.nan)
    pl = np.full(n, np.nan)
    k = p["sw"]
    for i in range(2 * k, n):
        w = h[i - 2 * k:i + 1]
        if (w[:k] < w[k]).all() and (w[k + 1:] <= w[k]).all():
            ph[i] = w[k]
        w = l[i - 2 * k:i + 1]
        if (w[:k] > w[k]).all() and (w[k + 1:] >= w[k]).all():
            pl[i] = w[k]
    rng = np.maximum(h - l, MT)
    num = ((c - l) / rng - (h - c) / rng) * v
    delta = ema_na(num, 7) / np.maximum(ema_na(v, 7), 1.0)
    rvol = v / np.maximum(np_sma(v, 20), 1.0)
    cp = np.r_[np.nan, c[:-1]]
    obv = np.cumsum(np.where(c > cp, v, np.where(c < cp, -v, 0.0)))
    obvma = np_sma(obv, 20)
    hlc3 = (h + l + c) / 3.0
    vw = np_vwap(df, hlc3)
    with np.errstate(invalid="ignore"):
        dscore = 50 + np.where(delta > 0, 12, -12) + np.where(obv > obvma, 8, -8) + np.where(c > vw, 8, -8) + np.where(rvol > p["rg"], 6, -3)
    dscore = np.clip(dscore, 0, 100)
    lam = 0.85
    al, be, ga = 1 - lam ** 3, 1.5 * (1 - lam) ** 2 * (1 + lam), 0.5 * (1 - lam) ** 3
    x = c[0]
    ve = ae = 0.0
    kin = np.zeros(n)
    aes = np.zeros(n)
    for i in range(n):
        xp = x + ve + 0.5 * ae
        vp = ve + ae
        res = c[i] - xp
        den = max(atr[i], MT) if not np.isnan(atr[i]) else np.nan
        boost = 1.8 if abs(res) / den > 3 else 1.0
        x = xp + al * boost * res
        ve = vp + be * boost * res
        ae = ae + ga * boost * res
        kin[i] = ve / den if den != 0 else 0.0
        aes[i] = ae
    lr = linreg(c, p["rl"])
    err = c - lr
    vp_, ve_ = var0(c, p["rl"]), var0(err, p["rl"])
    r2 = np.where(vp_ > 0, np.clip(1.0 - ve_ / np.where(vp_ > 0, vp_, 1.0), 0, 1), 0.0)
    r2 = np.where(np.isnan(ve_) & (vp_ > 0), np.nan, r2)
    slope = lr - np.r_[np.full(5, np.nan), lr[:-5]]
    S = dict(lph=np.nan, lpl=np.nan, st=0, le=None, ltr=np.nan, str_=np.nan, eb=None, prev=0.0)

    def orders(i, pos, info):
        out = []
        with np.errstate(invalid="ignore"):
            if not np.isnan(ph[i]):
                S["lph"] = ph[i]
            if not np.isnan(pl[i]):
                S["lpl"] = pl[i]
            if not np.isnan(S["lph"]) and c[i] > S["lph"] + atr[i] * 0.05:
                S["st"], S["lph"] = 1, np.nan
            if not np.isnan(S["lpl"]) and c[i] < S["lpl"] - atr[i] * 0.05:
                S["st"], S["lpl"] = -1, np.nan
            hb, hr = hc[i] > he[i], hc[i] < he[i]
            ab, ar = vote[i] >= 2, vote[i] <= -2
            kb = kin[i] > 0.10 and aes[i] >= 0
            kr = kin[i] < -0.10 and aes[i] <= 0
            rb = r2[i] >= p["mr"] and slope[i] > 0
            rr = r2[i] >= p["mr"] and slope[i] < 0
            vok = atr[i] / c[i] > 0.001
            sb = c[i] > e50[i] and e50[i] > e200[i]
            sr = c[i] < e50[i] and e50[i] < e200[i]
            ls = min(max((18 if S["st"] == 1 else 0) + (12 if hb else 0) + (18 if ab else 0) + (16 if kb else 0) + (16 if rb else 0) + (12 if dscore[i] > 55 else 0) + (8 if sb else 0), 0), 100)
            ss = min(max((18 if S["st"] == -1 else 0) + (12 if hr else 0) + (18 if ar else 0) + (16 if kr else 0) + (16 if rr else 0) + (12 if dscore[i] < 45 else 0) + (8 if sr else 0), 0), 100)
            cooled = S["le"] is None or i - S["le"] >= p["cd"]
            lent = bool(cooled and vok and ls >= 72 and delta[i] > p["dg"] and rvol[i] >= p["rg"])
            sent = bool(cooled and vok and ss >= 72 and delta[i] < -p["dg"] and rvol[i] >= p["rg"])
        if lent and pos <= 0:
            out.append(("entry", "CEM Long", 1, None, None))
            S["le"] = i
        if sent and pos >= 0:
            out.append(("entry", "CEM Short", -1, None, None))
            S["le"] = i
        if pos > 0:
            cand = c[i] - atr[i] * p["ta"]
            S["ltr"] = cand if S["prev"] <= 0 else max(S["ltr"] if not np.isnan(S["ltr"]) else cand, cand)
        else:
            S["ltr"] = np.nan
        if pos < 0:
            cand = c[i] + atr[i] * p["ta"]
            S["str_"] = cand if S["prev"] >= 0 else min(S["str_"] if not np.isnan(S["str_"]) else cand, cand)
        else:
            S["str_"] = np.nan
        avg = info["ep"] if pos != 0 else np.nan
        if pos > 0:
            lstop = max(avg - atr[i] * p["sa"], S["ltr"]) if (p["tr"] and not np.isnan(S["ltr"])) else avg - atr[i] * p["sa"]
            out.append(("exit", "CEM Long Exit", "CEM Long", lstop, avg + atr[i] * p["tg"]))
        if pos < 0:
            sstop = min(avg + atr[i] * p["sa"], S["str_"]) if (p["tr"] and not np.isnan(S["str_"])) else avg + atr[i] * p["sa"]
            out.append(("exit", "CEM Short Exit", "CEM Short", sstop, avg - atr[i] * p["tg"]))
        if pos != 0 and S["prev"] == 0:
            S["eb"] = i
        if pos == 0:
            S["eb"] = None
        texit = S["eb"] is not None and i - S["eb"] >= p["ts"]
        if pos > 0 and texit:
            out.append(("close", "CEM Long"))
        if pos > 0 and (S["st"] == -1 or ss > ls + 12):
            out.append(("close", "CEM Long"))
        if pos < 0 and texit:
            out.append(("close", "CEM Short"))
        if pos < 0 and (S["st"] == 1 or ls > ss + 12):
            out.append(("close", "CEM Short"))
        S["prev"] = pos
        return out

    ref = simulate_ord(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(htf=240, sw=5, al=6, dl=4, af=1.0, rl=80, mr=0.45, dg=0.03, rg=1.05, cd=8, sa=1.6, tg=2.8, tr=True, ta=1.8, ts=80)


def check():
    df = bars(24000, seed=61, freq="15min")
    for k_ in ("open", "high", "low", "close"):
        df[k_] = 100 * (df[k_] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Bias HTF": "60", "Structure pivot length": 3, "Minimum confidence": 0.30, "Delta pressure gate": 0.0, "Relative volume gate": 0.8, "Entry cooldown": 3, "Stop ATR": 1.2, "Target ATR": 2.0, "Time stop bars": 20},
              dict(htf=60, sw=3, mr=0.30, dg=0.0, rg=0.8, cd=3, sa=1.2, tg=2.0, ts=20)),
             ({"ALMA length": 10, "Deviation length": 6, "ALMA deviation factor": 0.5, "Trail ATR": 1.0, "Use trailing stop": False, "Regression confidence window": 40},
              dict(al=10, dl=6, af=0.5, ta=1.0, tr=False, rl=40)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
