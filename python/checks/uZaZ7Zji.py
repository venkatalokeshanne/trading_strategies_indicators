"""Independent check — Helios Institutional Synthesis Strategy [JOAT] (uZaZ7Zji): 15-minute bars (24 h synthetic) on a US stock chart (higher-timeframe periods counted from 09:30 New York, daily guard on the New York calendar day), orders at the bar close (process_orders_on_close), commission / slippage / margin off.
Adaptive baseline (EMA blended with a KAMA by the efficiency ratio, smoothed), ADX / ATR volatility score, session VWAP and its stdev channel, 120-bar range location, previous-day high / low and a 60-minute EMA bias (lookahead off, previous period), squeeze release, liquidity sweeps, momentum + volume pressure form an 8-point score; a trigger, cooldown, R-multiple and the daily equity guard gate entries (reversal allowed);
the quantity is risk-based (1% of equity over the stop distance), so equity is mirrored: initial capital + realised P&L of closed trades + open P&L at the bar close. Stop trails by ATR (never beyond entry), target ATR, regime-flip close, time guard, daily-guard close. Uses the pending-order reference broker (simulate_ord, on_close, with quantities).
Variants: defaults; score 3, cooldown 2, risk 2%, stop 1.2 / target 2.0 / trail 1.0 ATR, hold 40, 30-minute confirmation; session restriction + compression avoidance, a 0.5% daily guard and no regime-flip close."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_dmi, np_periods, np_rsi, np_security_lookahead_off, np_sma, np_tr, np_vwap, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "uZaZ7Zji"
MT = 0.01


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


def stdev0(x, n):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = x[i - n + 1:i + 1].std()
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


def clamp(x, lo, hi):
    return np.maximum(lo, np.minimum(hi, x))


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    dom = ny.dt.day.to_numpy()
    insess = (mins >= 570) & (mins < 960)
    hl3 = (h + l + c) / 3.0
    with np.errstate(invalid="ignore", divide="ignore"):
        atr = np_atr(h, l, c, 14)
        adx = np_dmi(h, l, c, 14)[2]
        abase = np_sma(atr, 50)
        adev = stdev0(atr, 50)
        vz = np.where(adev != 0, (atr - abase) / adev, 0.0)
        vscore = clamp(50.0 + 50.0 * np.tanh(vz / 2.0), 0.0, 100.0)
        atrp = np.where(c != 0, atr / c, 0.0) * 100.0
        cs = np.r_[np.nan, c[:-1]]
        cb = np.r_[np.full(14, np.nan), c[:-14]]
        chg = np.abs(c - cb)
        vs = wsum(np.abs(c - cs), 14)
        er = np.where(vs != 0, chg / vs, 0.0)
        fsc, ssc = 2.0 / (2 + 1.0), 2.0 / (30 + 1.0)
        sc = (er * (fsc - ssc) + ssc) ** 2
        kama = np.full(n, np.nan)
        for i in range(n):
            kama[i] = c[i] if (i == 0 or np.isnan(kama[i - 1])) else kama[i - 1] + sc[i] * (c[i] - kama[i - 1])
        el = ema_na(c, 34)
        blended = el + (kama - el) * clamp(er, 0.0, 1.0)
        base = ema_na(blended, 5)
        bsl = base - np.r_[np.nan, base[:-1]]
        ef, es = ema_na(c, 9), ema_na(c, 21)
        rsi = np_rsi(c, 14)
        t_up = (c > base) & (bsl > 0) & (ef > es)
        t_dn = (c < base) & (bsl < 0) & (ef < es)
        vw = np_vwap(df, hl3)
        sig = np.maximum(stdev0(hl3 - vw, 80), MT)
        vu1, vl1 = vw + sig, vw - sig
        rh, rl = roll(h, 120, np.max), roll(l, 120, np.min)
        span = np.maximum(rh - rl, MT)
        eq_, d25, p75 = rl + span * 0.5, rl + span * 0.25, rl + span * 0.75
        pidd, lastd = np_periods(df, 1440)
        nd = pidd[-1] + 1
        pdh_p = np.array([h[pidd == k].max() for k in range(nd)])
        pdl_p = np.array([l[pidd == k].min() for k in range(nd)])
        pdh = np_security_lookahead_off(np.r_[np.nan, pdh_p[:-1]], pidd, lastd)
        pdl = np_security_lookahead_off(np.r_[np.nan, pdl_p[:-1]], pidd, lastd)
        pidh, lasth = np_periods(df, p["htf"])
        pcl = c[lasth]
        hc = np_security_lookahead_off(np.r_[np.nan, pcl[:-1]], pidh, lasth)
        hf = np_security_lookahead_off(np.r_[np.nan, ema_na(pcl, 21)[:-1]], pidh, lasth)
        hs = np_security_lookahead_off(np.r_[np.nan, ema_na(pcl, 55)[:-1]], pidh, lasth)
        hbull, hbear = (hc > hf) & (hf > hs), (hc < hf) & (hf < hs)
        cmean = ema_na((base + vw) * 0.5, 20)
        cmult = 1.55 * (0.75 + clamp(vscore / 100.0, 0.0, 1.0))
        cu, cl_ = cmean + atr * cmult, cmean - atr * cmult
        bbb = np_sma(c, 20)
        bbd = stdev0(c, 20) * 2.0
        kcb = ema_na(c, 20)
        kcr = ema_na(np_tr(h, l, c, True), 20) * 1.5
        sqz = (bbb + bbd < kcb + kcr) & (bbb - bbd > kcb - kcr)
        sqz1 = np.r_[False, sqz[:-1]]
        sqr = (~sqz) & sqz1
        rrg = (adx < 18) & (vscore < 70)
        bullr, bearr = t_up & ~rrg, t_dn & ~rrg
        vbase = np_sma(v, 30)
        spike = v > vbase * 1.35
        spread = np.maximum(h - l, MT)
        delta = v * ((c - o) / spread)
        press = ema_na(delta / np.maximum(v, 1.0) * 100.0, 8)
        sh1 = np.r_[np.nan, h[:-1]]
        sl1 = np.r_[np.nan, l[:-1]]
        rsh, rsl = roll(sh1, 12, np.nanmax), roll(sl1, 12, np.nanmin)
        bsw = (~np.isnan(rsl)) & (l < rsl) & (c > rsl) & (c > o) & spike
        ssw = (~np.isnan(rsh)) & (h > rsh) & (c < rsh) & (c < o) & spike
        dbs = (~np.isnan(pdl)) & (l < pdl) & (c > pdl)
        dss = (~np.isnan(pdh)) & (h > pdh) & (c < pdh)
        ml = (rsi > 52) & (ef > es) & (press > -10)
        ms = (rsi < 48) & (ef < es) & (press < 10)
        vbl = (l <= vl1) & (c > vl1) & (c > o)
        vbs = (h >= vu1) & (c < vu1) & (c < o)
        crl = (l < cl_) & (c > cl_) & (c > o)
        crs = (h > cu) & (c < cu) & (c < o)
        vgate = (vscore >= 15.0) & (vscore <= 95.0) & (atrp <= 4.5)
        bcu = (c > base) & (np.r_[np.nan, c[:-1]] <= np.r_[np.nan, base[:-1]])
        bcd = (c < base) & (np.r_[np.nan, c[:-1]] >= np.r_[np.nan, base[:-1]])
        vcu = (c > vw) & (np.r_[np.nan, c[:-1]] <= np.r_[np.nan, vw[:-1]])
        vcd = (c < vw) & (np.r_[np.nan, c[:-1]] >= np.r_[np.nan, vw[:-1]])
        pdl_f = np.where(np.isnan(pdl), c - atr * p["sa"], pdl)
        pdh_f = np.where(np.isnan(pdh), c + atr * p["sa"], pdh)
        lsb = np.minimum(c - atr * p["sa"], pdl_f)
        ssb = np.maximum(c + atr * p["sa"], pdh_f)
    S = dict(le=None, ds=np.nan, prev=None, ae=np.nan, ast=np.nan, at=np.nan, aeb=None, rp=0, qm={})
    log: list = []

    def equity(i, pos, info):
        realized = sum(d * S["qm"][eb] * (xp - ep) for d, eb, ep, xb, xp in log)
        openp = pos * S["qm"][info["eb"]] * (c[i] - info["ep"]) if pos != 0 else 0.0
        return 100000.0 + realized + openp

    def orders(i, pos, info):
        out = []
        eqv = equity(i, pos, info)
        with np.errstate(invalid="ignore", divide="ignore"):
            prem_l = (c[i] < eq_[i]) or (c[i] < d25[i])
            prem_s = (c[i] > eq_[i]) or (c[i] > p75[i])
            dchg = i == 0 or dom[i] != dom[i - 1]
            S["ds"] = eqv if (np.isnan(S["ds"]) or dchg) else S["ds"]
            dd = (S["ds"] - eqv) / S["ds"] * 100.0 if S["ds"] > 0 else 0.0
            gok = p["mdl"] <= 0 or dd < p["mdl"]
            sess_ok = (not p["us"]) or bool(insess[i])
            slg = (not p["ac"]) or (not sqz[i])
            sl_ = sum(int(bool(x)) for x in (bullr[i], c[i] > vw[i], prem_l, ml[i], vgate[i], bsw[i] or dbs[i], vbl[i] or crl[i] or sqr[i], hbull[i]))
            ss_ = sum(int(bool(x)) for x in (bearr[i], c[i] < vw[i], prem_s, ms[i], vgate[i], ssw[i] or dss[i], vbs[i] or crs[i] or sqr[i], hbear[i]))
            rawl = sl_ >= p["ms"] and (bcu[i] or vcu[i] or bsw[i] or dbs[i] or vbl[i] or crl[i])
            raws = ss_ >= p["ms"] and (bcd[i] or vcd[i] or ssw[i] or dss[i] or vbs[i] or crs[i])
            can = S["le"] is None or i - S["le"] > p["cd"]
            ltb, stb = c[i] + atr[i] * p["ta"], c[i] - atr[i] * p["ta"]
            lrr = (ltb - c[i]) / (c[i] - lsb[i]) if (c[i] - lsb[i]) != 0 else 0.0
            srr = (c[i] - stb) / (ssb[i] - c[i]) if (ssb[i] - c[i]) != 0 else 0.0
            rlok = bool(lrr >= p["rr"] and c[i] > lsb[i] and gok)
            rsok = bool(srr >= p["rr"] and c[i] < ssb[i] and gok)
            lt = bool(sess_ok and can and vgate[i] and slg and rlok and rawl and pos <= 0)
            st_ = bool(sess_ok and can and vgate[i] and slg and rsok and raws and pos >= 0)

            def qty(entry, stop):
                sd = abs(entry - stop)
                raw = eqv * p["rk"] * 0.01 / max(sd, MT) if sd > MT else 0.0
                return max(0.0, min(raw, 100000.0))
        if lt:
            q = qty(c[i], lsb[i])
            S["qm"][i] = q
            out.append(("entry", "Long", 1, None, None, q))
            S["le"], S["ae"], S["ast"], S["at"], S["aeb"] = i, c[i], lsb[i], ltb, i
        if st_:
            q = qty(c[i], ssb[i])
            S["qm"][i] = q
            out.append(("entry", "Short", -1, None, None, q))
            S["le"], S["ae"], S["ast"], S["at"], S["aeb"] = i, c[i], ssb[i], stb, i
        if pos == 0 and S["prev"] is not None and S["prev"] != 0:
            S["ae"] = S["ast"] = S["at"] = np.nan
            S["aeb"] = None
        avg = info["ep"] if pos != 0 else np.nan
        if pos > 0:
            trail = c[i] - atr[i] * p["tr"]
            ast = S["ast"] if not np.isnan(S["ast"]) else avg - atr[i] * p["sa"]
            S["ast"] = min(max(ast, trail), avg - MT)
            S["at"] = S["at"] if not np.isnan(S["at"]) else avg + atr[i] * p["ta"]
            out.append(("exit", "Long Exit", "Long", S["ast"], S["at"]))
            if p["cf"] and bearr[i] and c[i] < base[i]:
                out.append(("close", "Long"))
        if pos < 0:
            trail = c[i] + atr[i] * p["tr"]
            ast = S["ast"] if not np.isnan(S["ast"]) else avg + atr[i] * p["sa"]
            S["ast"] = max(min(ast, trail), avg + MT)
            S["at"] = S["at"] if not np.isnan(S["at"]) else avg - atr[i] * p["ta"]
            out.append(("exit", "Short Exit", "Short", S["ast"], S["at"]))
            if p["cf"] and bullr[i] and c[i] > base[i]:
                out.append(("close", "Short"))
        bit = i - S["aeb"] if S["aeb"] is not None else 0
        if pos > 0 and bit >= p["mh"]:
            out.append(("close", "Long"))
        if pos < 0 and bit >= p["mh"]:
            out.append(("close", "Short"))
        if (not gok) and pos > 0:
            out.append(("close", "Long"))
        if (not gok) and pos < 0:
            out.append(("close", "Short"))
        S["prev"] = pos
        return out

    ref = simulate_ord(o, h, l, c, orders, on_close=True, log=log)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(htf=60, sa=1.8, ta=2.8, tr=1.35, rr=1.0, ms=4, cd=4, rk=1.0, mh=120, mdl=3.0, us=False, ac=False, cf=True)


def check():
    df = bars(30000, seed=52, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.4
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Min Confluence Score": 3, "Cooldown Bars": 2, "Risk % per Trade": 2.0, "ATR Stop Multiple": 1.2, "ATR Target Multiple": 2.0, "ATR Trail Multiple": 1.0, "Max Hold Bars": 40, "Confirmation Timeframe": "30"},
              dict(ms=3, cd=2, rk=2.0, sa=1.2, ta=2.0, tr=1.0, mh=40, htf=30)),
             ({"Restrict to Session": True, "Avoid Fresh Compression": True, "Daily Equity Guard %": 0.5, "Close On Regime Flip": False}, dict(us=True, ac=True, mdl=0.5, cf=False)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
