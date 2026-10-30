"""Independent check — Code A - Terminal Core (X5M5zevX): daily bars, market orders at the next open (a close only acts when a position is open at the script run). Components: Hull trend core HMA15(hl2) with next-value projection h[1] + (h[1] - h[6]) / 5 (rising/falling gate hLime / hRed); wave oscillator: e = EMA9(hlc3), d = EMA9(|hlc3 - e|), ci = (hlc3 - e) / (0.015 d), w1 = EMA12(ci), w2 = SMA3(w1), diff = round(w1 - w2, 1); money flow = SMA60(200 (close - open) / (high - low)) - 2.25; stochastic averages SMA2(stoch 40) / SMA2(stoch 80); bias score = WMA5 of the 10-term count (+1 / -1 for close vs close[11..20]) x 100/12; run-count of closes above/below close[4]; Wilder parabolic SAR (0.01, 0.01, 0.1) written from the Pine documentation. The 17 filters and their and/or combinations follow the source (flags below). Entries "L+" / "S-"; exits by candle colour and wave difference.
Variants: shadowless filter off (the default set never fires on this data); many filters off (difference, candle momentum, high/low, series, PSAR, shadowless, strategy bands); the same with 'Wave & EMA Combined' and the colour exit off."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, np_sma, np_stoch, np_wma, run_conversion, simulate

TV_ID = "X5M5zevX"


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


def sma_na(x, n):
    """SMA from a running prefix sum, the way Pine's ta.sma accumulates (matters when the two stochastic averages tie)."""
    x = np.asarray(x, float)
    nanc = np.r_[0, np.cumsum(np.isnan(x))]
    P = np.r_[0.0, np.cumsum(np.where(np.isnan(x), 0.0, x))]
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        if nanc[i + 1] - nanc[i - n + 1] == 0:
            out[i] = (P[i] - P[i - (n - 1)] + x[i]) / n
    return out


def rnd(x):
    return int(np.floor(x + 0.5))


def sar(h, l, c, start, inc, mx):
    n = len(c)
    out = np.full(n, np.nan)
    result = maxmin = acc = np.nan
    below = False
    for i in range(1, n):
        first = False
        if i == 1:
            if c[i] > c[i - 1]:
                below, maxmin, result = True, h[i], l[i - 1]
            else:
                below, maxmin, result = False, l[i], h[i - 1]
            first = True
            acc = start
        result = result + acc * (maxmin - result)
        if below:
            if result > l[i]:
                first, below = True, False
                result, maxmin, acc = max(h[i], maxmin), l[i], start
        else:
            if result < h[i]:
                first, below = True, True
                result, maxmin, acc = min(l[i], maxmin), h[i], start
        if not first:
            if below:
                if h[i] > maxmin:
                    maxmin, acc = h[i], min(acc + inc, mx)
            else:
                if l[i] < maxmin:
                    maxmin, acc = l[i], min(acc + inc, mx)
        if below:
            result = min(result, l[i - 1])
            if i > 1:
                result = min(result, l[i - 2])
        else:
            result = max(result, h[i - 1])
            if i > 1:
                result = max(result, h[i - 2])
        out[i] = result
    return out


def one(df, params, F, w0, w1):
    import warnings
    warnings.simplefilter("ignore")
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    sh = lambda x, k=1: np.r_[np.full(k, np.nan), x[:-k]]
    hl2, hlc3 = (h + l) / 2, (h + l + c) / 3
    hm = np_wma(2 * np_wma(hl2, 15 // 2) - np_wma(hl2, 15), rnd(np.sqrt(15)))
    h1, h6 = sh(hm), sh(hm, 6)
    nb = h1 + (h1 - h6) / 5
    curve = np.where(hm > nb, 1, -1)
    ea, eb, ec = np_ema(c, 5), np_ema(c, 11), np_ema(c, 33)
    e = np_ema(hlc3, 9)
    d = ema_na(np.abs(hlc3 - e), 9)
    with np.errstate(divide="ignore", invalid="ignore"):
        ci = (hlc3 - e) / (0.015 * d)
        ci[~np.isfinite(ci)] = np.nan
        oa = ema_na(ci, 12)
        ob = sma_na(oa, 3)
        odf = np.floor((oa - ob) * 10 + 0.5) / 10
        mfr = (c - o) / (h - l) * 200
        mfr[~np.isfinite(mfr)] = np.nan
        omf = sma_na(mfr, 60) - 2.25
    k1 = sma_na(np_stoch(c, h, l, 40), 2)
    k2 = sma_na(np_stoch(c, h, l, 80), 2)
    sc = np.zeros(n)
    for i in range(n):
        s = 0
        for k in range(11, 21):
            s += 1 if (i >= k and c[i] > c[i - k]) else -1
        sc[i] = s
    bsv = np_wma(sc, 5) * (100.0 / 12.0)
    up, dn = np.zeros(n), np.zeros(n)
    for i in range(n):
        up[i] = (up[i - 1] if i else 0) + 1 if (i >= 4 and c[i] > c[i - 4]) else 0
        dn[i] = (dn[i - 1] if i else 0) + 1 if (i >= 4 and c[i] < c[i - 4]) else 0
    ev_u, ev_d = [], []
    runu, rund = np.full(n, np.nan), np.full(n, np.nan)
    for i in range(n):
        pu = up[i - 1] if i else np.nan
        pdn = dn[i - 1] if i else np.nan
        if up[i] < pu:
            ev_u.append(up[i])
        if dn[i] < pdn:
            ev_d.append(dn[i])
        runu[i] = up[i] - ev_u[-2] if len(ev_u) >= 2 else np.nan
        rund[i] = dn[i] - ev_d[-2] if len(ev_d) >= 2 else np.nan
    anc = sar(h, l, c, 0.01, 0.01, 0.1)
    S = dict(gl=True, gs=True)
    pc = sh(c)
    po, ph, pl = sh(o), sh(h), sh(l)
    oa2, ob2 = sh(oa, 2), sh(ob, 2)
    oa3, ob3 = sh(oa, 3), sh(ob, 3)
    bsp = sh(bsv)
    hlp = h1

    def cross(a, b, pa, pb, upd=True):
        with np.errstate(invalid="ignore"):
            return (a > b and pa <= pb) if upd else (a < b and pa >= pb)

    def orders(i, pos):
        out = []
        with np.errstate(invalid="ignore"):
            lime = curve[i] != -1 and hm[i] > hlp[i]
            red = curve[i] != 1 and hm[i] < hlp[i]
            if not lime:
                S["gl"] = True
            if not red:
                S["gs"] = True
            cA0 = lime if F[9] else True
            cA1 = red if F[9] else True
            cA2 = (k1[i] > k2[i]) if F[6] else True
            cA3 = (k1[i] <= k2[i]) if F[6] else True
            cA4 = (omf[i] > 0) if F[7] else True
            cA5 = (omf[i] <= 0) if F[7] else True
            cA6 = (bsv[i] > bsp[i] or bsv[i] >= 83 or bsv[i] <= -83) if F[8] else True
            cA7 = (bsv[i] < bsp[i] or bsv[i] <= -83 or bsv[i] >= 83) if F[8] else True
            cA8 = (v[i] >= 0) if F[10] else True
            cA9 = (runu[i] <= 3) if F[11] else True
            cB0 = (rund[i] <= 3) if F[11] else True
            cB1 = (c[i] > anc[i]) if F[12] else True
            cB2 = (c[i] < anc[i]) if F[12] else True
            cB3 = (o[i] > po[i] and c[i] > pc[i]) if F[4] else True
            cB4 = (o[i] < po[i] and c[i] < pc[i]) if F[4] else True
            cB5 = (ph[i] < h[i]) if F[5] else True
            cB6 = (pl[i] > l[i]) if F[5] else True
            cB7 = (min(o[i], c[i]) == l[i]) if F[14] else True
            cB8 = (max(o[i], c[i]) == h[i]) if F[14] else True
            cB9 = (ob[i] < 70) if F[16] else True
            cC0 = (ob[i] > -70) if F[16] else True
            cC1 = (ob[i] < -70) if F[15] else True
            cC2 = (ob[i] > 70) if F[15] else True
            cC3 = (odf[i] >= 5) if F[0] else True
            cC4 = (odf[i] <= -5) if F[0] else True
            xwl = F[2] and (cross(oa[i], ob[i], sh(oa)[i], sh(ob)[i]) or cross(oa2[i], ob2[i], oa3[i], ob3[i]))
            xws = F[2] and (cross(oa[i], ob[i], sh(oa)[i], sh(ob)[i], False) or cross(oa2[i], ob2[i], oa3[i], ob3[i], False))
            xel = F[3] and cross(eb[i], ec[i], sh(eb)[i], sh(ec)[i])
            xes = F[3] and cross(ea[i], eb[i], sh(ea)[i], sh(eb)[i], False)
            if not F[2] and not F[3]:
                xwl = xws = xel = xes = True
            xl = (xel and xwl) if F[1] else (xel or xwl)
            xs = (xes and xws) if F[1] else (xes or xws)
            pal = ob[i] > 0 and cA4 and cB9
            pas = ob[i] < 0 and cA5 and cC0
            pbl = ob[i] < 0 and cA2 and cC1
            pbs = ob[i] > 0 and cA3 and cC2
            sig_up = (cB5 and xl and cA9 and cB1) and (cB3 and cB7 and cC3) and (cA0 and (pal or pbl) and cA6 and cA8 and S["gl"])
            sig_dn = (cB6 and xs and cB0 and cB2) and (cB4 and cB8 and cC4) and (cA1 and (pas or pbs) and cA7 and cA8 and S["gs"])
            if F[17]:
                if sig_up:
                    S["gl"] = False
                if sig_dn:
                    S["gs"] = False
            xlc = (c[i] < o[i]) if w0 else True
            xsc = (c[i] > o[i]) if w0 else True
            xld = (odf[i] <= 0.2) if w1 else True
            xsd = (odf[i] >= 0.2) if w1 else True
            exl, exs = xlc and xld, xsc and xsd
        if sig_up:
            out.append(("entry", 1))
        if sig_dn:
            out.append(("entry", -1))
        if exl and pos > 0:
            out.append(("close", 1))
        if exs and pos < 0:
            out.append(("close", -1))
        return out

    ref = simulate(o, h, l, c, orders)
    ok, dd = compare(run_conversion(TV_ID, df, params=params, strategy_overrides={"commission_value": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{dd} (got {len(ref)})"


def check():
    df = bars(6000, seed=273)
    msgs, allok = [], True
    F0 = {k: True for k in range(18)}
    F0[1] = False
    F0[13] = True
    loose = dict(F0)
    for k in (0, 4, 5, 11, 12, 14, 15, 16):
        loose[k] = False
    loose2 = dict(loose)
    loose2[1] = True
    names = {0: "Difference Comparison", 4: "Candle Momentum", 5: "High/Low Update", 11: "Series Filter", 12: "PSAR Bias", 14: "Shadowless Filter", 15: "Strategy #1 Filter", 16: "Strategy #2 Filter"}
    pl = {names[k]: False for k in names}
    F1 = dict(F0)
    F1[14] = False
    cases = (({"Shadowless Filter": False}, F1, True, True),
             (pl, loose, True, True),
             (dict(pl, **{"Wave & EMA Combined": True, "Exit by Candle Color": False}), loose2, False, True))
    for params, F, w0, w1 in cases:
        ok, m = one(df, params, F, w0, w1)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
