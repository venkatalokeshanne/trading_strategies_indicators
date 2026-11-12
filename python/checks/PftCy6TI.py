"""Independent check — Concordia Regime Execution [JOAT] (PftCy6TI): hourly bars of a 24 h crypto market (UTC days, ISO weeks), market orders at the next open, margin / commission / slippage off. Score engine: regime (ADX >= floor, choppiness index 100 log10(sum TR / range)/log10(n) below a ceiling, 34-bar range / (ATR x 34) not compressed), five-to-six trend votes (EMA 8/21/55 stack, two slopes, close vs day / week VWAP), pivot-based break of structure and sweeps, a six-RSI ribbon (each RSI turned into EMA(s + (s - s[lag]))), a z-score pressure composite (volume delta, VWAP distance, basis distance, ATR) and a crowding risk gauge. Setup = score >= threshold and the soft gates and a trigger (BOS / sweep / ribbon cross / close x> fast EMA) while not already in that direction (reverses); while a trade is open at script time an ATR stop (trailing once the trigger R is reached) and target from the average entry price are issued, and a bias failure closes it. Uses the pending-order reference broker (simulate_ord).
Variants: defaults; weekly VWAP alignment with a cooldown of 3 bars; looser regime (ADX floor 10, no chop limit) with different ribbon settings and no bias-failure exit."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_dmi, np_ema, np_rsi, np_tr, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "PftCy6TI"


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


def zs(x, n):
    s = pd.Series(x)
    mean, dev = s.rolling(n).mean().to_numpy(), s.rolling(n).std(ddof=0).to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(dev != 0, (x - mean) / dev, 0.0)


def rmax(x, n):
    return pd.Series(x).rolling(n).max().to_numpy()


def rmin(x, n):
    return pd.Series(x).rolling(n).min().to_numpy()


def cu(a, b):
    pa, pb = np.r_[np.nan, a[:-1]], np.r_[np.nan, b[:-1]]
    with np.errstate(invalid="ignore"):
        return (a > b) & (pa <= pb)


def cd(a, b):
    pa, pb = np.r_[np.nan, a[:-1]], np.r_[np.nan, b[:-1]]
    with np.errstate(invalid="ignore"):
        return (a < b) & (pa >= pb)


def vwap(df, hl3, v, keyfn):
    n = len(hl3)
    out = np.zeros(n)
    pv = vv = 0.0
    for i in range(n):
        if i == 0 or keyfn[i] != keyfn[i - 1]:
            pv = vv = 0.0
        pv += hl3[i] * v[i]
        vv += v[i]
        out[i] = pv / vv if vv > 0 else hl3[i]
    return out


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    tick = SymbolInfo.make("TEST:SYNTH", "crypto", qty_step=1e-9).mintick
    dt = pd.to_datetime(df["time"], unit="ms", utc=True)
    day = dt.dt.date.to_numpy()
    iso = dt.dt.isocalendar()
    wk = [(int(a), int(b)) for a, b in zip(iso["year"], iso["week"])]
    hl3 = (h + l + c) / 3
    sv = vwap(df, hl3, v, day)
    wv = vwap(df, hl3, v, wk)
    atr = np_atr(h, l, c, 14)
    adx = np_dmi(h, l, c, 14)[2]
    with np.errstate(invalid="ignore", divide="ignore"):
        trs = pd.Series(np_tr(h, l, c, True)).rolling(14).sum().to_numpy()
        crange = rmax(h, 14) - rmin(l, 14)
        chop = np.where(crange > 0, 100 * np.log10(trs / crange) / np.log10(14), 50.0)
        comprange = rmax(h, 34) - rmin(l, 34)
        cratio = np.where(atr * 34 > 0, comprange / (atr * 34), 1.0)
        comp = cratio < 0.80
        expansion = (adx >= p["adxf"]) & (chop < p["chopc"]) & ~comp
        fe, me, se = np_ema(c, 8), np_ema(c, 21), np_ema(c, 55)
        basis = (fe + me + se) / 3.0
        sl = lambda e: e - np.r_[np.full(5, np.nan), e[:-5]]
        fs, ms_, ss = sl(fe), sl(me), sl(se)
        vote = (np.where(fe > me, 1, -1) + np.where(me > se, 1, -1) + np.where(fs > 0, 1, -1) + np.where(ms_ > 0, 1, -1) + np.where(c > sv, 1, -1))
        if p["weekly"]:
            vote = vote + np.where(c > wv, 1, -1)
        tbias = np.where(vote >= 3, 1, np.where(vote <= -3, -1, 0))
        # swings
        lsh = np.full(n, np.nan)
        lsl = np.full(n, np.nan)
        sh = sl_ = np.nan
        for i in range(n):
            j = i - 3
            if j >= 3:
                if h[j] > h[j - 3:j].max() and h[j] >= h[j + 1:i + 1].max():
                    sh = h[j]
                if l[j] < l[j - 3:j].min() and l[j] <= l[j + 1:i + 1].min():
                    sl_ = l[j]
            lsh[i], lsl[i] = sh, sl_
        c1 = np.r_[np.nan, c[:-1]]
        bbos = ~np.isnan(lsh) & (c > lsh) & (c1 <= lsh)
        sbos = ~np.isnan(lsl) & (c < lsl) & (c1 >= lsl)
        sbias = np.zeros(n, int)
        cur = 0
        for i in range(n):
            if bbos[i]:
                cur = 1
            if sbos[i]:
                cur = -1
            sbias[i] = cur
        ssw = ~np.isnan(lsl) & (l < lsl) & (c > lsl)
        bsw = ~np.isnan(lsh) & (h > lsh) & (c < lsh)
        os_ = []
        for k in range(6):
            r = np_rsi(c, p["rbase"] + p["rstep"] * k)
            lag = (p["rsm"] - 1) // 2
            sh_ = np.r_[np.full(lag, np.nan), r[:n - lag]] if lag else r
            os_.append(ema_na(r + (r - sh_), p["rsm"]) - 50)
        frb = (os_[0] + os_[1] + os_[2]) / 3.0
        srb = (os_[3] + os_[4] + os_[5]) / 3.0
        spread = frb - srb
        mbias = np.where(spread > p["rthr"], 1, np.where(spread < -p["rthr"], -1, 0))
        vdp = (c - o) / np.fmax(h - l, tick) * v
        vdz, vwz, vlz, bz = zs(vdp, 55), zs(c - sv, 55), zs(atr, 55), zs(c - basis, 55)
        pres = 0.35 * vdz + 0.25 * vwz + 0.20 * bz - 0.20 * vlz
        crowd = 0.50 * zs(np_rsi(c, 14) - 50, 55) + 0.50 * zs(c - wv, 55)
        pbias = np.where(pres > 0.0, 1, np.where(pres < -0.0, -1, 0))
        liq = 50.0 + np.abs(crowd) * 14.0 + np.maximum(vlz, 0) * 10.0 + np.where(bsw | ssw, 8.0, 0.0)
        liq = np.where(np.isnan(liq), np.nan, np.maximum(0, np.minimum(100, liq)))
        rok = liq < 92.0
        ls = (np.where(expansion, 18, 0) + np.where(tbias == 1, 22, 0) + np.where(sbias == 1, 14, 0) + np.where(bbos, 12, 0) + np.where(ssw, 8, 0)
              + np.where(mbias == 1, 16, 0) + np.where(pbias == 1, 10, 0) + np.where(c > sv, 8, 0)
              + (np.where(c > wv, 6, 0) if p["weekly"] else 0) - np.where(rok, 0, 30)).astype(float)
        ss_ = (np.where(expansion, 18, 0) + np.where(tbias == -1, 22, 0) + np.where(sbias == -1, 14, 0) + np.where(sbos, 12, 0) + np.where(bsw, 8, 0)
               + np.where(mbias == -1, 16, 0) + np.where(pbias == -1, 10, 0) + np.where(c < sv, 8, 0)
               + (np.where(c < wv, 6, 0) if p["weekly"] else 0) - np.where(rok, 0, 30)).astype(float)
        softx = expansion | (adx >= p["adxf"] * 0.60)
        softr = liq < 95.0
        ltrig = bbos | ssw | cu(frb, srb) | cu(c, fe)
        strig = sbos | bsw | cd(frb, srb) | cd(c, fe)
        lset = (ls >= 30.0) & (ls >= ss_ - 8) & softx & (tbias >= 0) & (mbias >= 0) & (pres > -0.50) & ltrig & softr
        sset = (ss_ >= 30.0) & (ss_ >= ls - 8) & softx & (tbias <= 0) & (mbias <= 0) & (pres < 0.50) & strig & softr
    S = dict(le=None)

    def orders(i, pos, info):
        out = []
        cdr = S["le"] is None or i - S["le"] >= p["cool"]
        if lset[i] and cdr and pos <= 0:
            out.append(("entry", "Long", 1, None, None))
            S["le"] = i
        if sset[i] and cdr and pos >= 0:
            out.append(("entry", "Short", -1, None, None))
            S["le"] = i
        ep = info.get("ep", np.nan)
        with np.errstate(invalid="ignore"):
            a = atr[i]
            lstop, ltgt = ep - a * 1.4, ep + a * 2.2
            sstop, stgt = ep + a * 1.4, ep - a * 2.2
            lta = pos > 0 and c[i] >= ep + a * 1.4 * 0.8
            sta = pos < 0 and c[i] <= ep - a * 1.4 * 0.8
            ltr = rmax(h[:i + 1][-5:], 5)[-1] - a * 1.1 if i >= 4 else np.nan
            st_ = rmin(l[:i + 1][-5:], 5)[-1] + a * 1.1 if i >= 4 else np.nan
            lse = (np.nan if np.isnan(lstop) or np.isnan(ltr) else max(lstop, ltr)) if lta else lstop
            sse = (np.nan if np.isnan(sstop) or np.isnan(st_) else min(sstop, st_)) if sta else sstop
        nn = lambda x: None if np.isnan(x) else x
        if pos > 0:
            out.append(("exit", "Long Exit", "Long", nn(lse), nn(ltgt)))
        if pos < 0:
            out.append(("exit", "Short Exit", "Short", nn(sse), nn(stgt)))
        if p["fail"] and pos > 0 and (tbias[i] != 1 or mbias[i] == -1 or pbias[i] == -1 or not rok[i]):
            out.append(("close", "Long"))
        if p["fail"] and pos < 0 and (tbias[i] != -1 or mbias[i] == 1 or pbias[i] == 1 or not rok[i]):
            out.append(("close", "Short"))
        return out

    ref = simulate_ord(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, tf="60", params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(adxf=18.0, chopc=60.0, weekly=False, rbase=7, rstep=3, rsm=5, rthr=0.6, cool=0, fail=True)


def check():
    df = bars(5000, seed=63, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Require Weekly VWAP Alignment": True, "Cooldown Bars": 3}, dict(weekly=True, cool=3)),
             ({"ADX Floor": 10.0, "Chop Ceiling": 80.0, "Ribbon Base": 5, "Ribbon Step": 2, "Lag-Reduced Smoothing": 4, "Spread Threshold": 0.3, "Exit On Bias Failure": False},
              dict(adxf=10.0, chopc=80.0, rbase=5, rstep=2, rsm=4, rthr=0.3, fail=False)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
