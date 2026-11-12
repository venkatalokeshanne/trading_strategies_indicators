"""Independent check — Singularity Convergence Protocol [JOAT] (GZCiUApZ): daily bars, market orders at the next open, margin / commission / slippage off. Eight vote engines: (1) volume-flow index + Laguerre RSI + Fisher + TSI + MFI + OBV / A-D normalised + CMF momentum, (2) order block / fair value gap / market structure with premium / discount, (3) multi-EMA momentum wave with +/-6 sigma bands, (4) liquidity sweeps with a 2.25x volume surge, (5) hull + supertrend-direction + EMA alignment + ADX trend, (6) price / RSI pivot divergence (valuewhen-based) confirmed by MACD / TSI / stochastic, (7) Bollinger-inside-Keltner squeeze breakout with a low volatility index, (8) institutional flow phase. The sum of votes plus bonus points and the signed score decide the entry; the stop / target are measured from the signal close and a ratcheting ATR trail is issued while the trade is open. Uses the pending-order reference broker (simulate_ord).
Variants: defaults (confluence scoring, min 2); min signals 1 without confluence scoring; stop 1 ATR, R:R 3, no trail; confluence with min 3 and a 2 ATR trail."""
import math

import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_dmi, np_ema, np_rsi, np_sma, run_conversion, simulate_ord

TV_ID = "GZCiUApZ"


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


def sh(x, k):
    return np.r_[np.full(k, np.nan), x[:len(x) - k]]


def rstd(x, n):
    return pd.Series(x).rolling(n).std(ddof=0).to_numpy()


def rsum(x, n):
    return pd.Series(x).rolling(n).sum().to_numpy()


def wext(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        w = w[~np.isnan(w)]
        if len(w):
            out[i] = fn(w)
    return out


def hi(x, n):
    return wext(x, n, np.max)


def lo(x, n):
    return wext(x, n, np.min)


def cum(x):
    return np.cumsum(np.where(np.isnan(x), 0.0, x))


def dv(a, b):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(b == 0, np.nan, a / b)


def wma(x, n):
    out = np.full(len(x), np.nan)
    w = np.arange(1, n + 1, dtype=float)
    for i in range(n - 1, len(x)):
        seg = x[i - n + 1:i + 1]
        if not np.isnan(seg).any():
            out[i] = (seg * w).sum() / w.sum()
    return out


def alma(x, n, off, sig):
    out = np.full(len(x), np.nan)
    m = off * (n - 1)
    s = n / sig
    wt = np.exp(-((np.arange(n) - m) ** 2) / (2 * s * s))
    for i in range(n - 1, len(x)):
        seg = x[i - n + 1:i + 1]
        if not np.isnan(seg).any():
            out[i] = (seg * wt).sum() / wt.sum()
    return out


def piv(x, left, right, high):
    out = np.full(len(x), np.nan)
    for i in range(left + right, len(x)):
        w = x[i - left - right:i + 1]
        if np.isnan(w).any():
            continue
        ctr = w[left]
        a, b = w[:left], w[left + 1:]
        if (high and (a < ctr).all() and (b <= ctr).all()) or ((not high) and (a > ctr).all() and (b >= ctr).all()):
            out[i] = ctr
    return out


def rising(x, n):
    out = np.zeros(len(x), bool)
    for i in range(n, len(x)):
        out[i] = all(x[i] > x[i - k] for k in range(1, n + 1))
    return out


def falling(x, n):
    out = np.zeros(len(x), bool)
    for i in range(n, len(x)):
        out[i] = all(x[i] < x[i - k] for k in range(1, n + 1))
    return out


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    with np.errstate(invalid="ignore", divide="ignore"):
        typ = (h + l + c) / 3
        typ1, c1 = sh(typ, 1), sh(c, 1)
        vinter = np.log(typ) - np.log(typ1)
        cutoff = 0.2 * rstd(vinter, 30) * c
        vave = sh(np_sma(v, 14), 1)
        vmax = vave * 2.5
        vc = np.where(v < vmax, v, vmax)
        mf = typ - typ1
        vcp = np.where(mf > cutoff, vc, np.where(mf < -cutoff, -vc, 0.0))
        vfi = dv(np_sma(vcp, 14) * 14, vave) * 4.0
        # Laguerre
        g = 0.4
        L = np.zeros((4, n))
        for i in range(n):
            p0 = L[:, i - 1] if i else np.zeros(4)
            L[0, i] = (1 - g) * c[i] + g * p0[0]
            L[1, i] = -g * L[0, i] + p0[0] + g * p0[1]
            L[2, i] = -g * L[1, i] + p0[1] + g * p0[2]
            L[3, i] = -g * L[2, i] + p0[2] + g * p0[3]
        cu = np.maximum(np.maximum(L[0] - L[1], 0) + np.maximum(L[1] - L[2], 0) + np.maximum(L[2] - L[3], 0), 0.0001)
        cd = np.maximum(np.maximum(L[1] - L[0], 0) + np.maximum(L[2] - L[1], 0) + np.maximum(L[3] - L[2], 0), 0.0001)
        lrsi = (cu / (cu + cd) - 0.5) * 100
        comp = (vfi + lrsi) / 2
        fi = 0.1 * (comp / 1.5)
        fv = (np.exp(2 * fi) - 1) / (np.exp(2 * fi) + 1)
        fsm = ema_na(fv, 7)
        pc = c - c1
        tsi = 100 * dv(ema_na(ema_na(pc, 25), 13), ema_na(ema_na(np.abs(pc), 25), 13))
        rmf = typ * v
        posf = np.where(typ > typ1, rmf, 0.0)
        negf = np.where(typ < typ1, rmf, 0.0)
        mfi = 100 - dv(np.full(n, 100.0), 1 + dv(rsum(posf, 14), rsum(negf, 14)))
        obv = cum(np.sign(c - c1) * v)
        obvn = dv(obv - lo(obv, 100), hi(obv, 100) - lo(obv, 100)) * 100 - 50
        mfv = dv((c - l) - (h - c), h - l) * v
        adl = cum(mfv)
        ads = ema_na(adl, 14)
        adn = dv(ads - lo(ads, 100), hi(ads, 100) - lo(ads, 100)) * 100 - 50
        cmf = dv(np_sma(mfv, 20), np_sma(v, 20))
        core = (vfi * 0.20) + (lrsi * 0.20) + (fsm * 20 * 0.15) + (tsi / 2 * 0.15) + ((mfi - 50) / 2 * 0.10) + (obvn * 0.10) + (adn * 0.05) + (cmf * 50 * 0.05)
        msm = ema_na(core, 7)
        mbull = (msm > 0) & (msm > sh(msm, 1))
        mbear = (msm < 0) & (msm < sh(msm, 1))
        mscore = np.where(mbull, 1.0, np.where(mbear, -1.0, 0.0))
    ph10, pl10 = piv(h, 10, 10, True), piv(l, 10, 10, False)
    n_ = np.isnan
    bob = np.nan
    boa = False
    beob = np.nan
    bea = False
    bull_ob = np.zeros(n, bool)
    bear_ob = np.zeros(n, bool)
    ms = np.zeros(n, int)
    lhh = lll = np.nan
    cur_ms = 0
    with np.errstate(invalid="ignore"):
        for i in range(n):
            if not n_(pl10[i]) and c[i] > (h[i - 10] if i >= 10 else np.nan):
                bob, boa = l[i - 11] if i >= 11 else np.nan, True
            if boa and c[i] < bob:
                boa = False
            if not n_(ph10[i]) and c[i] < (l[i - 10] if i >= 10 else np.nan):
                beob, bea = h[i - 11] if i >= 11 else np.nan, True
            if bea and c[i] > beob:
                bea = False
            bull_ob[i], bear_ob[i] = boa, bea
            if not n_(ph10[i]):
                if n_(lhh) or ph10[i] > lhh:
                    lhh = ph10[i]
                    if cur_ms != 1:
                        cur_ms = 1
                else:
                    cur_ms = -1
            if not n_(pl10[i]):
                if n_(lll) or pl10[i] < lll:
                    lll = pl10[i]
                    if cur_ms != -1:
                        cur_ms = -1
                else:
                    cur_ms = 1
            ms[i] = cur_ms
        bfvg = l > sh(h, 2)
        efvg = h < sh(l, 2)
        eqm = (hi(h, 50) + lo(l, 50)) / 2
        sbull = (bull_ob | bfvg) & (ms == 1) & (c < eqm)
        sbear = (bear_ob | efvg) & (ms == -1) & (c > eqm)
        sscore = np.where(sbull, 1.0, np.where(sbear, -1.0, 0.0))
        # wave
        mom = c - sh(c, 21)
        alb = alma(c, 9, 0.85, 6)
        aadj = alb - (alb - mom)
        m1, m2, m3, m4, m5 = (ema_na(mom, k) for k in (9, 21, 55, 100, 200))
        b1, b2, b3, b4, b5 = (m1 + m2) / 2, (m2 + m3) / 2, (m3 + m4) / 2, (m4 + m5) / 2, (m5 + m1) / 2
        ball = (b1 + b2 + b3 + b4 + b5) / 5
        origin = np_sma(ball, 25)
        dev = 6.0 * rstd(ball, 25)
        tb, bb_ = origin + dev, origin - dev
        allb = (mom > b1) & (mom > b2) & (mom > b3) & (mom > b4) & (mom > b5)
        allr = ((mom <= b1) & (mom <= aadj)) & ((mom <= b2) & (mom <= aadj)) & ((mom <= b3) & (mom <= aadj)) & ((mom <= b4) & (mom <= aadj)) & ((mom <= b5) & (mom <= aadj))
        extb = (b1 > tb) & (aadj > tb) & (aadj > sh(aadj, 3))
        extr = (b1 < bb_) & (aadj < bb_) & (aadj < sh(aadj, 3))
        spr = b1 - b5
        wb = (b1 > b2) & rising(b1, 2) & (spr > 5)
        wr = (b1 < b2) & falling(b1, 2) & (spr < -5)
        wscore = np.where(wb | allb, 1.0, np.where(wr | allr, -1.0, 0.0))
    # liquidity
    ph_, pl_ = ph10, pl10
    bl = sl_ = np.nan
    lbull = np.zeros(n, bool)
    lbear = np.zeros(n, bool)
    avgv = np_sma(v, 45)
    with np.errstate(invalid="ignore"):
        surge = v > avgv * 2.25
        for i in range(n):
            if not n_(ph_[i]):
                bl = ph_[i]
            if not n_(pl_[i]):
                sl_ = pl_[i]
            lbull[i] = (not n_(sl_)) and l[i] < sl_ and surge[i]
            lbear[i] = (not n_(bl)) and h[i] > bl and surge[i]
    lscore = np.where(lbull, 1.0, np.where(lbear, -1.0, 0.0))
    # trend
    hull = wma(2 * wma(c, 10) - wma(c, 20), 4)
    atr10 = np_atr(h, l, c, 10)
    src2 = (h + l) / 2
    ub, lb = src2 + 3.0 * atr10, src2 - 3.0 * atr10
    dirn = np.zeros(n, int)
    with np.errstate(invalid="ignore"):
        for i in range(n):
            dirn[i] = -1 if c[i] > ub[i] else (1 if c[i] < lb[i] else (dirn[i - 1] if i else 1))
    adx = np_dmi(h, l, c, 14)[2]
    e9, e21, e50 = np_ema(c, 9), np_ema(c, 21), np_ema(c, 50)
    with np.errstate(invalid="ignore"):
        tbull = rising(hull, 3) & (dirn == -1) & (adx > 20) & (e9 > e21) & (e21 > e50)
        tbear = falling(hull, 3) & (dirn == 1) & (adx > 20) & (e9 < e21) & (e21 < e50)
    tscore = np.where(tbull, 1.0, np.where(tbear, -1.0, 0.0))
    # divergence
    rsi = np_rsi(c, 14)
    macd = np_ema(c, 12) - np_ema(c, 26)
    with np.errstate(invalid="ignore", divide="ignore"):
        tsi2 = tsi
        hh14, ll14 = hi(h, 14), lo(l, 14)
        stk = 100.0 * dv(c - ll14, hh14 - ll14)
        stks = np_sma(stk, 3)
        cosc = (rsi - 50) + macd + tsi2 + (stks - 50)
    rph, rpl = piv(rsi, 5, 5, True), piv(rsi, 5, 5, False)
    ev_pl, ev_rpl, ev_ph, ev_rph = [], [], [], []
    bdiv = rdiv = False
    cscore = 0
    cs_arr = np.zeros(n, int)
    bd = np.zeros(n, bool)
    rd = np.zeros(n, bool)
    with np.errstate(invalid="ignore"):
        for i in range(n):
            ppl = ev_pl[-1] if ev_pl else np.nan
            prpl = ev_rpl[-1] if ev_rpl else np.nan
            pph = ev_ph[-1] if ev_ph else np.nan
            prph = ev_rph[-1] if ev_rph else np.nan
            if not n_(pl_[i]) and not n_(rpl[i]):
                if pl_[i] < ppl and rpl[i] > prpl:
                    bdiv, cscore = True, 0
                    cscore += int(rpl[i] > prpl) + int(macd[i] > (macd[i - 5] if i >= 5 else np.nan)) + int(tsi2[i] > (tsi2[i - 5] if i >= 5 else np.nan)) + int(stks[i] > (stks[i - 5] if i >= 5 else np.nan))
                else:
                    bdiv = False
            if not n_(ph_[i]) and not n_(rph[i]):
                if ph_[i] > pph and rph[i] < prph:
                    rdiv, cscore = True, 0
                    cscore += int(rph[i] < prph) + int(macd[i] < (macd[i - 5] if i >= 5 else np.nan)) + int(tsi2[i] < (tsi2[i - 5] if i >= 5 else np.nan)) + int(stks[i] < (stks[i - 5] if i >= 5 else np.nan))
                else:
                    rdiv = False
            if not n_(pl_[i]):
                ev_pl.append(pl_[i])
            if not n_(rpl[i]):
                ev_rpl.append(rpl[i])
            if not n_(ph_[i]):
                ev_ph.append(ph_[i])
            if not n_(rph[i]):
                ev_rph.append(rph[i])
            bd[i], rd[i], cs_arr[i] = bdiv, rdiv, cscore
        dbull = bd & (cs_arr >= 2) & (cosc < -20)
        dbear = rd & (cs_arr >= 2) & (cosc > 20)
    dscore = np.where(dbull, 1.0, np.where(dbear, -1.0, 0.0))
    # volatility
    atrs = ema_na(np_atr(h, l, c, 14), 7)
    with np.errstate(invalid="ignore", divide="ignore"):
        atrp = dv(atrs - lo(atrs, 100), hi(atrs, 100) - lo(atrs, 100)) * 100
        bmid = np_sma(c, 20)
        bsd = rstd(c, 20)
        bup, blw = bmid + 2.0 * bsd, bmid - 2.0 * bsd
        bw = dv(bup - blw, bmid) * 100
        bwp = dv(bw - lo(bw, 100), hi(bw, 100) - lo(bw, 100)) * 100
        kb = np_ema(c, 20)
        kr = np_atr(h, l, c, 20) * 1.5
        sqon = (blw > kb - kr) & (bup < kb + kr)
        sqprev = np.r_[False, sqon[:-1]]
        sqbo = sqprev & ~sqon
        ret = np.log(dv(c, c1))
        hv = rstd(ret, 20) * math.sqrt(252) * 100
        hvp = dv(hv - lo(hv, 100), hi(hv, 100) - lo(hv, 100)) * 100
        vidx = (atrp + bwp + hvp) / 3
        vbull = sqbo & (c > c1) & (vidx < 40)
        vbear = sqbo & (c < c1) & (vidx < 40)
        vscore = np.where(vbull, 1.0, np.where(vbear, -1.0, 0.0))
        # institutional
        cmf2 = cmf
        mfi2 = mfi
        obvn2 = dv(obv - lo(obv, 100), hi(obv, 100) - lo(obv, 100)) * 100
        adn2 = dv(ads - lo(ads, 100), hi(ads, 100) - lo(ads, 100)) * 100
        flow = (cmf2 * 50 + (mfi2 - 50) + (obvn2 - 50) + (adn2 - 50)) / 4
    phase = np.zeros(n, int)
    cur = 0
    with np.errstate(invalid="ignore"):
        for i in range(n):
            if flow[i] > 30 and cmf2[i] > 0.1 and mfi2[i] > 50:
                cur = 2
            elif flow[i] > 10 and cmf2[i] > 0:
                cur = 1
            elif flow[i] < -30 and cmf2[i] < -0.1 and mfi2[i] < 50:
                cur = -2
            elif flow[i] < -10 and cmf2[i] < 0:
                cur = -1
            else:
                cur = 0
            phase[i] = cur
        ibull = (phase >= 1) & (flow > 10) & (cmf2 > 0) & (mfi2 > 50)
        ibear = (phase <= -1) & (flow < -10) & (cmf2 < 0) & (mfi2 < 50)
    iscore = np.where(ibull, 1.0, np.where(ibear, -1.0, 0.0))
    bsig = mbull.astype(int) + sbull + wb + lbull + tbull + dbull + vbull + ibull
    rsig = mbear.astype(int) + sbear + wr + lbear + tbear + dbear + vbear + ibear
    ctot = mscore + sscore + wscore + lscore + tscore + dscore + vscore + iscore
    with np.errstate(invalid="ignore"):
        bbon = extb.astype(int) + allb + (cs_arr == 4) + (surge & (flow > 20))
        rbon = extr.astype(int) + allr + (cs_arr == 4) + (surge & (flow < -20))
    tb_ = bsig + bbon + np.where(ctot > 0, ctot, 0)
    tr_ = rsig + rbon + np.where(ctot < 0, np.abs(ctot), 0)
    if p["conf"]:
        lsig = (tb_ >= p["minsig"]) & (tb_ > tr_)
        ssig = (tr_ >= p["minsig"]) & (tr_ > tb_)
    else:
        lsig = (bsig >= p["minsig"]) & (bsig > rsig)
        ssig = (rsig >= p["minsig"]) & (rsig > bsig)
    atr = np_atr(h, l, c, 10)

    def orders(i, pos):
        out = []
        a = atr[i]
        with np.errstate(invalid="ignore"):
            if lsig[i]:
                out += [("entry", "LONG", 1, None, None), ("exit", "Exit Long", "LONG", c[i] - a * p["sl"], c[i] + a * p["sl"] * p["rr"])]
            if ssig[i]:
                out += [("entry", "SHORT", -1, None, None), ("exit", "Exit Short", "SHORT", c[i] + a * p["sl"], c[i] - a * p["sl"] * p["rr"])]
            if p["trail"] and pos > 0:
                out.append(("exit", "Trail Long", "LONG", c[i] - a * p["tatr"], None))
            if p["trail"] and pos < 0:
                out.append(("exit", "Trail Short", "SHORT", c[i] + a * p["tatr"], None))
        return [(x[0],) + tuple(None if (isinstance(y, float) and np.isnan(y)) else y for y in x[1:]) for x in out]

    with np.errstate(invalid="ignore"):
        ref = simulate_ord(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(conf=True, minsig=2, sl=2.0, rr=2.0, trail=True, tatr=3.0)


def check():
    df = bars(3500, seed=4242)
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.6
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Minimum Signals": 1, "Use Confluence Scoring": False}, dict(minsig=1, conf=False)),
             ({"Stop Loss (ATR)": 1.0, "Take Profit (R:R)": 3.0, "Use Trailing Stop": False}, dict(sl=1.0, rr=3.0, trail=False)),
             ({"Minimum Signals": 3, "Trailing ATR": 2.0}, dict(minsig=3, tatr=2.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
