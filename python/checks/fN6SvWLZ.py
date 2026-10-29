"""Independent check — CRMI v6 Core Strategy Alpha (fN6SvWLZ): daily bars, market orders at the signal close (process_orders_on_close), margin / commission off. Major (10) / minor (4) pivot structure (higher highs and lows from the last two pivots of each kind), EMA 20/50/200 trend state (-3..3) with slopes over 10 bars, value state (retracement of the last impulse or EMA34 +/- ATR band), regime state (trend efficiency = |net move| / summed travel over 20 bars, ATR %), reaction / trigger counts and the five sub-scores; entries (FAST / LONG / HYBRID) only while flat and after the cool-down, within the per-cycle limits; the stop / target from the last minor swing and ATR are issued while the trade is open at script time, and a thesis failure (close beyond the EMA34 and a minor structure shift) closes it. Uses the pending-order reference broker (simulate_ord, on_close).
Variants: defaults (HYBRID); FAST mode with a lower score and no trend filter; LONG mode with a lower score and a shorter cool-down; HYBRID without trend filter, short cycle limit 1 and no re-entry."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "fN6SvWLZ"


def pivots(x, left, right, high):
    out = np.full(len(x), False)
    for i in range(left + right, len(x)):
        w = x[i - left - right:i + 1]
        if np.isnan(w).any():
            continue
        ctr = w[left]
        a, b = w[:left], w[left + 1:]
        out[i] = ((a < ctr).all() and (b <= ctr).all()) if high else ((a > ctr).all() and (b >= ctr).all())
    return out


def swing_state(h, l, ln):
    n = len(h)
    ph, pl = pivots(h, ln, ln, True), pivots(l, ln, ln, False)
    h1, h2, l1, l2 = (np.full(n, np.nan) for _ in range(4))
    a1 = a2 = b1 = b2 = np.nan
    for i in range(n):
        if ph[i]:
            a2, a1 = a1, h[i - ln]
        if pl[i]:
            b2, b1 = b1, l[i - ln]
        h1[i], h2[i], l1[i], l2[i] = a1, a2, b1, b2
    return h1, h2, l1, l2


def shift(x, k):
    return np.r_[np.full(k, np.nan), x[:len(x) - k]]


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    tick = SymbolInfo.make("TEST:SYNTH", "crypto", qty_step=1e-9).mintick
    atr = np_atr(h, l, c, 14)
    eq = np_ema(c, 34)
    up_b, lo_b = eq + atr * 1.0, eq - atr * 1.0
    tf, tm, ts = np_ema(c, 20), np_ema(c, 50), np_ema(c, 200)
    sf, sm, ss = tf - shift(tf, 10), tm - shift(tm, 10), ts - shift(ts, 10)
    mh1, mh2, ml1, ml2 = swing_state(h, l, 10)
    nh1, nh2, nl1, nl2 = swing_state(h, l, 4)
    with np.errstate(invalid="ignore", divide="ignore"):
        above = (c > tf) & (c > tm) & (c > ts)
        below = (c < tf) & (c < tm) & (c < ts)
        valid_major = ~np.isnan(mh1) & ~np.isnan(mh2) & ~np.isnan(ml1) & ~np.isnan(ml2)
        valid_minor = ~np.isnan(nh1) & ~np.isnan(nh2) & ~np.isnan(nl1) & ~np.isnan(nl2)
        mbull, mbear = valid_major & (mh1 > mh2) & (ml1 > ml2), valid_major & (mh1 < mh2) & (ml1 < ml2)
        nbull, nbear = valid_minor & (nh1 > nh2) & (nl1 > nl2), valid_minor & (nh1 < nh2) & (nl1 < nl2)
        mbias = np.where(mbull & ~mbear, 1, np.where(mbear & ~mbull, -1, 0))
        nbias = np.where(nbull & ~nbear, 1, np.where(nbear & ~nbull, -1, 0))
        nbs = ~np.isnan(nh1) & (c > nh1)
        nrs = ~np.isnan(nl1) & (c < nl1)
        baligned = (tf > tm) & (tm > ts) & (sf > 0) & (sm > 0)
        raligned = (tf < tm) & (tm < ts) & (sf < 0) & (sm < 0)
        tstate = np.select([above & baligned & (ss > 0), (c > tm) & (sm > 0), c > ts, below & raligned & (ss < 0), (c < tm) & (sm < 0), c < ts], [3, 2, 1, -3, -2, -1], 0)
        ilow = np.where(mbias != 0, ml1, nl1)
        ihigh = np.where(mbias != 0, mh1, nh1)
        irange = np.where(~np.isnan(ihigh) & ~np.isnan(ilow), np.abs(ihigh - ilow), np.nan)
        rb = np.where(~np.isnan(irange) & (irange > 0), (ihigh - c) / irange, np.nan)
        rr_ = np.where(~np.isnan(irange) & (irange > 0), (c - ilow) / irange, np.nan)
        deepd = ((mbias == 1) & ~np.isnan(rb) & (rb >= p["deep"])) | (c < lo_b)
        disc = ((mbias == 1) & ~np.isnan(rb) & (rb >= p["bal"])) | (c < eq)
        deepp = ((mbias == -1) & ~np.isnan(rr_) & (rr_ >= p["deep"])) | (c > up_b)
        prem = ((mbias == -1) & ~np.isnan(rr_) & (rr_ >= p["bal"])) | (c > eq)
        vstate = np.select([deepd, disc, deepp, prem], [2, 1, -2, -1], 0)
        net = np.abs(c - shift(c, 20))
        trav = pd.Series(np.abs(c - shift(c, 1))).rolling(20).sum().to_numpy()
        eff = np.where(trav == 0.0, 0.0, net / trav)
        apct = np.where(c == 0.0, 0.0, atr / c) * 100.0
        disorder = apct > 2.2
        texp = (eff > 0.45) & (np.abs(tstate) >= 2)
        pcont = (np.abs(tstate) >= 2) & (vstate != 0)
        rrot = (eff < 0.25) & (np.abs(tstate) <= 1)
        trans = (eff >= 0.25) & (eff <= 0.45) & (np.abs(tstate) <= 2)
        regime = np.select([disorder, texp, pcont, rrot, trans], [-2, 2, 1, 0, -1], 0)
        mode = p["mode"]
        minscore = {"FAST": p["fmin"], "LONG": p["lmin"], "HYBRID": p["hmin"]}[mode]
        mm = {"LONG": 1.5, "FAST": 0.8, "HYBRID": (0.8 + 1.5) / 2.0}[mode]
        body = np.abs(c - o)
        b1 = shift(body, 1)
        uw, lw = h - np.fmax(o, c), np.fmin(o, c) - l
        bullc, bearc = c > o, c < o
        c1, h1_, l1_ = shift(c, 1), shift(h, 1), shift(l, 1)
        i8 = lambda b: b.astype(int)
        brc = (i8((body < b1) & bearc) + i8(lw > body) + i8((l <= lo_b) | (c < eq)) + i8(c > l + (h - l) * 0.55) + i8(c > c1))
        src = (i8((body < b1) & bullc) + i8(uw > body) + i8((h >= up_b) | (c > eq)) + i8(c < l + (h - l) * 0.45) + i8(c < c1))
        brv, srv = brc >= 2, src >= 2
        e8 = np_ema(c, 8)
        bmc = i8(bullc) + i8(c > e8) + i8(~np.isnan(nl1) & (c > nl1))
        smc = i8(bearc) + i8(c < e8) + i8(~np.isnan(nh1) & (c < nh1))
        btrig = nbs | ((c > h1_) & (c > eq)) | (bmc >= 2)
        strig = nrs | ((c < l1_) & (c < eq)) | (smc >= 2)
        cl = lambda x, hi: np.clip(x, 0, hi)
        sl_ = cl(10 * (mbias == 1) + 5 * (nbias >= 0) + 5 * nbs + 5 * ~mbear, 25)
        vl_ = cl(10 * disc + 10 * deepd + 5 * (c <= lo_b), 25)
        tl_ = cl(np.select([tstate == 3, tstate == 2, tstate == 1], [15, 10, 5], 0) + 5 * baligned, 20)
        rl_ = cl(5 * brv + 5 * (lw > body) + 5 * btrig, 15)
        ss_ = cl(10 * (mbias == -1) + 5 * (nbias <= 0) + 5 * nrs + 5 * ~mbull, 25)
        vs_ = cl(10 * prem + 10 * deepp + 5 * (c >= up_b), 25)
        ts_ = cl(np.select([tstate == -3, tstate == -2, tstate == -1], [15, 10, 5], 0) + 5 * raligned, 20)
        rs_ = cl(5 * srv + 5 * (uw > body) + 5 * strig, 15)
        lref = np.where(np.isnan(nl1), l, nl1)
        sref = np.where(np.isnan(nh1), h, nh1)
        lstop, sstop = lref - atr * mm, sref + atr * mm
        lrisk, srisk = c - lstop, sstop - c
        ltgt, stgt = c + lrisk * 1.5, c - srisk * 1.5
        lrr = np.where(lrisk == 0.0, 0.0, (ltgt - c) / lrisk)
        srr = np.where(srisk == 0.0, 0.0, (c - stgt) / srisk)
        kl_ = cl(5 * (lrisk > tick * 10) + 5 * (lrr >= 1.2) + 5 * np.where(~np.isnan(mh1), ltgt <= mh1 * 1.03, True), 15)
        ks_ = cl(5 * (srisk > tick * 10) + 5 * (srr >= 1.2) + 5 * np.where(~np.isnan(ml1), stgt >= ml1 * 0.97, True), 15)
        bscore, sscore = sl_ + vl_ + tl_ + rl_ + kl_, ss_ + vs_ + ts_ + rs_ + ks_
        tr_on = p["trend"]
        tl_ok = (not tr_on) | (tstate >= 2)
        ts_ok = (not tr_on) | (tstate <= -2)
        fl_ok = (not tr_on) | (tstate >= -1)
        fs_ok = (not tr_on) | (tstate <= 1)
        hl_ok = (not tr_on) | (tstate >= 1)
        hs_ok = (not tr_on) | (tstate <= -1)
        mlt = tl_ok if mode == "LONG" else (fl_ok if mode == "FAST" else hl_ok)
        mst = ts_ok if mode == "LONG" else (fs_ok if mode == "FAST" else hs_ok)
        if mode == "LONG":
            mreg = (regime == 2) | (regime == 1)
        elif mode == "FAST":
            mreg = regime != -2
        else:
            mreg = (regime == 2) | (regime == 1) | (regime == -1)
        isfast = mode == "FAST"
        nol = ~np.isnan(mh1) & ((mh1 - c) < atr * 0.8)
        nos = ~np.isnan(ml1) & ((c - ml1) < atr * 0.8)
        conflict = (mbias == 0) & (nbias == 0)
        bctx = ((mbias == 1) | (isfast & (mbias == 0))) & (vstate >= 1) & mreg & mlt & ~nol & ~disorder & ~conflict
        sctx = ((mbias == -1) | (isfast & (mbias == 0))) & (vstate <= -1) & mreg & mst & ~nos & ~disorder & ~conflict
        rvl = (lrr >= 1.2) & (lrisk > tick * 10)
        rvs = (srr >= 1.2) & (srisk > tick * 10)
        midr = vstate == 0
    S = dict(pp=None, leb=None, lc=0, sc=0, ld=0, ls=np.nan, lt=np.nan, ss=np.nan, st=np.nan)
    nn = lambda x: None if np.isnan(x) else x

    def orders(i, pos):
        out = []
        pp, S["pp"] = S["pp"], pos
        if pos == 0 and pp is not None and pp != 0:
            S["leb"] = i
        cd = S["leb"] is not None and i - S["leb"] < p["cool"]
        if mbias[i] == 1 and (i == 0 or mbias[i - 1] != 1):
            S["lc"] = 0
        if mbias[i] == -1 and (i == 0 or mbias[i - 1] != -1):
            S["sc"] = 0
        lcb, scb = S["lc"] >= p["maxc"], S["sc"] >= p["maxc"]
        sdl = p["one"] and S["ld"] == 1 and not p["reent"]
        sds = p["one"] and S["ld"] == -1 and not p["reent"]
        la = bool(bctx[i] and brv[i] and btrig[i] and bscore[i] >= minscore and rvl[i] and not cd and not lcb and not sdl and not midr[i] and pos == 0)
        sa = bool(sctx[i] and srv[i] and strig[i] and sscore[i] >= minscore and rvs[i] and not cd and not scb and not sds and not midr[i] and pos == 0)
        if la:
            S.update(ls=lstop[i], lt=ltgt[i], lc=S["lc"] + 1, ld=1)
            out.append(("entry", "CRMI Long", 1, None, None))
        if sa:
            S.update(ss=sstop[i], st=stgt[i], sc=S["sc"] + 1, ld=-1)
            out.append(("entry", "CRMI Short", -1, None, None))
        if pos > 0:
            out.append(("exit", "CRMI Long Exit", "CRMI Long", nn(S["ls"]), nn(S["lt"])))
        if pos < 0:
            out.append(("exit", "CRMI Short Exit", "CRMI Short", nn(S["ss"]), nn(S["st"])))
        with np.errstate(invalid="ignore"):
            if pos > 0 and c[i] < eq[i] and nrs[i]:
                out.append(("close", "CRMI Long"))
            if pos < 0 and c[i] > eq[i] and nbs[i]:
                out.append(("close", "CRMI Short"))
        return out

    ref = simulate_ord(o, h, l, c, orders, on_close=True)
    ok, d = compare(run_conversion(TV_ID, df, params=params, strategy_overrides={"commission_value": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(deep=0.70, bal=0.50, mode="HYBRID", fmin=65, lmin=80, hmin=72, cool=8, one=True, reent=True, maxc=2, trend=True)


def check():
    df = bars(6000, seed=2024)
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Execution Mode": "FAST", "Fast Min Score": 45, "Use Trend Confirmation": False}, dict(mode="FAST", fmin=45, trend=False)),
             ({"Execution Mode": "LONG", "Long Min Score": 60, "Cooldown Bars After Exit": 2}, dict(mode="LONG", lmin=60, cool=2)),
             ({"Hybrid Min Score": 50, "Use Trend Confirmation": False, "Max Trades Per Direction Cycle": 1, "Allow Re-entry": False, "Balanced Pullback Threshold": 0.3},
              dict(hmin=50, trend=False, maxc=1, reent=False, bal=0.3)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
