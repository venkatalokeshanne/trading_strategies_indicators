"""Independent check — Crownmark Allocation Engine [JOAT] (Wf07I8Bf): daily bars, market orders at the signal close (process_orders_on_close), margin / commission off. Regime score = 35 x scaled(EMA21 - EMA55 over 55 bars) + 10 x clamp(z(regression-slope change)) + 25 x clamp((ADX-20)/25) x sign + 20 x clamp(2 ER - 1) x sign + 5 x clamp(z(stdev/sma)) x sign; KAMA baseline (efficiency ratio over 34 bars, fast 4 / slow 26, squared smoothing) with an ATR/stdev corridor; pullback into the inner corridor; rolling 80-bar volume-weighted value area (partial windows at the start); effort / result / location pressure composite with EMA and signal; price-vs-oscillator pivot divergence guard; stop / target from the average entry price (bounded by the corridor and the KAMA trail) issued while a trade is open at script time; opposite-signal, context-failure (regime, pressure, baseline, bars in trade counted from the last flat-to-open transition, divergence) closes. Uses the pending-order reference broker (simulate_ord, on_close).
Variants: defaults; hlc3 source with lower regime thresholds and no auction / VWAP / expansion requirements; pressure threshold 5, 12-bar limit, no opposite-signal flatten, no divergence guard."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_dmi, np_ema, np_rsi, np_sma, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "Wf07I8Bf"


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


def rstd(x, n):
    return pd.Series(x).rolling(n).std(ddof=0).to_numpy()


def zscore(x, n):
    mean = pd.Series(x).rolling(n).mean().to_numpy()
    dev = rstd(x, n)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(dev > 0, (x - mean) / dev, 0.0)


def linreg(y, n, offset):
    out = np.full(len(y), np.nan)
    xs = np.arange(n, dtype=float)
    sx, sxx = xs.sum(), (xs * xs).sum()
    den = n * sxx - sx * sx
    for i in range(n - 1, len(y)):
        w = y[i - n + 1:i + 1]
        if np.isnan(w).any():
            continue
        sy, sxy = w.sum(), (xs * w).sum()
        slope = (n * sxy - sx * sy) / den
        out[i] = (sy - slope * sx) / n + slope * (n - 1 - offset)
    return out


def wmax(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        w = w[~np.isnan(w)]
        if len(w):
            out[i] = fn(w)
    return out


def pivots(x, left, right, high):
    out = np.full(len(x), False)
    for i in range(left + right, len(x)):
        w = x[i - left - right:i + 1]
        if np.isnan(w).any():
            continue
        ctr = w[left]
        a, b = w[:left], w[left + 1:]
        if high:
            out[i] = (a < ctr).all() and (b <= ctr).all()
        else:
            out[i] = (a > ctr).all() and (b >= ctr).all()
    return out


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    tick = SymbolInfo.make("TEST:SYNTH", "crypto", qty_step=1e-9).mintick
    hl3 = (h + l + c) / 3
    s = hl3 if p["src"] == "hlc3" else c
    atr = np_atr(h, l, c, 14)
    adx = np_dmi(h, l, c, 14)[2]
    fe, se = np_ema(s, 21), np_ema(s, 55)
    with np.errstate(invalid="ignore", divide="ignore"):
        mov = lambda ln: np.array([sum(abs(s[i - k] - s[i - k - 1]) for k in range(ln)) if i >= ln else np.nan for i in range(n)])
        net = lambda ln: np.array([abs(s[i] - s[i - ln]) if i >= ln else np.nan for i in range(n)])
        m20, n20 = mov(20), net(20)
        eff = np.where(np.abs(m20) > 1e-10, n20 / m20, 0.0)
        volexp = rstd(c, 21) / np.fmax(np_sma(c, 21), tick)
        spread = fe - se
        slope = linreg(spread, 21, 0) - linreg(spread, 21, 1)
        lo55, hi55 = wmax(spread, 55, np.min), wmax(spread, 55, np.max)
        span = hi55 - lo55
        tscore = np.where(span > 0, (spread - lo55) / span * 2.0 - 1.0, 0.0) * 35.0
        sscore = np.clip(zscore(slope, 21), -2.0, 2.0) * 10.0
        sg = np.sign(spread)
        strength = np.clip((adx - 20.0) / 25.0, -1.0, 1.0) * 25.0 * sg
        escore = np.clip(eff * 2.0 - 1.0, -1.0, 1.0) * 20.0 * sg
        vscore = np.clip(zscore(volexp, 21), -2.0, 2.0) * 5.0 * sg
        regime = tscore + sscore + strength + escore + vscore
        # KAMA
        m34, n34 = mov(34), net(34)
        er = np.where(m34 > 0, n34 / m34, 0.0)
        fsc, ssc = 2.0 / 5.0, 2.0 / 27.0
        sm = (er * (fsc - ssc) + ssc) ** 2
        kama = np.zeros(n)
        for i in range(n):
            kama[i] = s[i] if i == 0 else kama[i - 1] + sm[i] * (s[i] - kama[i - 1])
        kprev = np.r_[np.nan, kama[:-1]]
        hw = (np_atr(h, l, c, 34) * 0.65 + rstd(s, 34) * 0.35) * 1.8
        upc, loc = kama + hw, kama - hw
        iu, il = kama + hw * 0.5, kama - hw * 0.5
        btr = (c > kama) & (kama > kprev)
        str_ = (c < kama) & (kama < kprev)
        pbl = (l <= iu) & (c > kama - atr * 0.35)
        pbs = (h >= il) & (c < kama + atr * 0.35)
        rv = np.array([v[max(0, i - 79):i + 1].sum() for i in range(n)])
        pvs = np.array([(hl3 * v)[max(0, i - 79):i + 1].sum() for i in range(n)])
        rvw = np.where(rv > 0, pvs / rv, np_sma(hl3, 80))
        asg = rstd(hl3, 80) * p["adev"]
        ahi, alo = rvw + asg, rvw - asg
        aok = (~np.full(n, p["reqauc"])) | ((c >= alo) & (c <= ahi))
        vl = (~np.full(n, p["reqvw"])) | (c >= rvw)
        vs = (~np.full(n, p["reqvw"])) | (c <= rvw)
        trg = np.fmax(h - l, tick)
        body = c - o
        cloc = ((c - l) - (h - c)) / trg
        sv34 = np_sma(v, 34)
        relv = np.where(np.abs(sv34) > 1e-10, v / sv34, 1.0)
        effort = np.clip(body / trg, -1.0, 1.0)
        sd_ = np.where(np.abs(atr) > 1e-10, body / atr, 0.0)
        ex = np.exp(2.0 * (sd_ * 4.0))
        res = (ex - 1.0) / (ex + 1.0)
        loca = np.clip(cloc, -1.0, 1.0)
        praw = (effort * 0.40 + res * 0.35 + loca * 0.25) * relv * 100.0
        pc = np_ema(praw, p["psm"])
        psig = ema_na(pc, max(2, int(p["psm"] * 1.5)))
        rz = zscore(trg, 21)
        plok = (pc > p["pthr"]) & (pc > psig) & ((not p["reqexp"]) | (rz > -0.10))
        psok = (pc < -p["pthr"]) & (pc < psig) & ((not p["reqexp"]) | (rz > -0.10))
        rsi = np_rsi(c, 14)
        c8 = np.r_[np.full(8, np.nan), c[:-8]]
        roc = 100.0 * (c - c8) / c8
        osc = ema_na((rsi - 50.0) * 1.2 + roc, 3)
    pph, ppl = pivots(h, 5, 5, True), pivots(l, 5, 5, False)
    oph, opl = pivots(osc, 5, 5, True), pivots(osc, 5, 5, False)
    bear_ev = np.zeros(n, bool)
    bull_ev = np.zeros(n, bool)
    pph_v = pch_v = ppl_v = pcl_v = np.nan
    for i in range(n):
        if pph[i] and oph[i]:
            ch, co = h[i - 5], osc[i - 5]
            bear_ev[i] = not np.isnan(pph_v) and ch > pph_v and co < pch_v
            pph_v, pch_v = ch, co
        if ppl[i] and opl[i]:
            cl, co = l[i - 5], osc[i - 5]
            bull_ev[i] = not np.isnan(ppl_v) and cl < ppl_v and co > pcl_v
            ppl_v, pcl_v = cl, co

    def recent(ev):
        out = np.zeros(n, bool)
        last = None
        for i in range(n):
            if ev[i]:
                last = i
            out[i] = last is not None and i - last < 18
        return out

    rbear, rbull = recent(bear_ev), recent(bull_ev)
    dlok = (not p["usediv"]) | ~rbear
    dsok = (not p["usediv"]) | ~rbull
    with np.errstate(invalid="ignore"):
        lsig = (regime > p["bull"]) & (btr & pbl & (c <= upc)) & aok & vl & plok & dlok
        ssig = (regime < p["bear"]) & (str_ & pbs & (c >= loc)) & aok & vs & psok & dsok
    S = dict(pp=None, eb=None)
    nn = lambda x: None if np.isnan(x) else x
    mx = lambda a, b: np.nan if np.isnan(a) or np.isnan(b) else max(a, b)
    mn = lambda a, b: np.nan if np.isnan(a) or np.isnan(b) else min(a, b)

    def orders(i, pos, info):
        out = []
        pp, S["pp"] = S["pp"], pos
        if lsig[i] and pos <= 0:
            out.append(("entry", "Long Crownmark", 1, None, None))
        if ssig[i] and pos >= 0:
            out.append(("entry", "Short Crownmark", -1, None, None))
        if pos != 0 and pp == 0:
            S["eb"] = i
        if pos == 0:
            S["eb"] = None
        bars_in = i - S["eb"] if (pos != 0 and S["eb"] is not None) else 0
        ep = info.get("ep", np.nan)
        a = atr[i]
        with np.errstate(invalid="ignore"):
            if pos > 0:
                lp = mx(ep - a * p["stopm"], loc[i] - a * 0.25)
                lt = kama[i] - a * 1.1
                out.append(("exit", "Long Crownmark Exit", "Long Crownmark", nn(mx(lp, lt)), nn(ep + a * p["tgtm"])))
            if pos < 0:
                sp = mn(ep + a * p["stopm"], upc[i] + a * 0.25)
                stt = kama[i] + a * 1.1
                out.append(("exit", "Short Crownmark Exit", "Short Crownmark", nn(mn(sp, stt)), nn(ep - a * p["tgtm"])))
            lf = pos > 0 and (regime[i] < 0 or pc[i] < 0 or c[i] < kama[i] or bars_in >= p["maxb"] or rbear[i])
            sf = pos < 0 and (regime[i] > 0 or pc[i] > 0 or c[i] > kama[i] or bars_in >= p["maxb"] or rbull[i])
        if p["flat"] and ssig[i] and pos > 0:
            out.append(("close", "Long Crownmark"))
        elif lf:
            out.append(("close", "Long Crownmark"))
        if p["flat"] and lsig[i] and pos < 0:
            out.append(("close", "Short Crownmark"))
        elif sf:
            out.append(("close", "Short Crownmark"))
        return out

    ref = simulate_ord(o, h, l, c, orders, on_close=True)
    ok, d = compare(run_conversion(TV_ID, df, params=params, strategy_overrides={"commission_value": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(src="close", bull=18.0, bear=-18.0, adev=1.0, reqauc=True, reqvw=True, reqexp=True, psm=8, pthr=12.0, usediv=True, stopm=1.8, tgtm=3.2, maxb=40, flat=True)


def check():
    df = bars(4000, seed=222)
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.6
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Source": "hlc3", "Bull Regime Threshold": 8.0, "Bear Regime Threshold": -8.0, "Require Auction Acceptance": False, "Require VWAP Alignment": False, "Require Volatility Expansion": False},
              dict(src="hlc3", bull=8.0, bear=-8.0, reqauc=False, reqvw=False, reqexp=False)),
             ({"Pressure Threshold": 5.0, "Maximum Bars In Trade": 12, "Flatten On Opposite Signal": False, "Use Divergence Guard": False, "Bull Regime Threshold": 10.0,
               "Bear Regime Threshold": -10.0, "Value Area Width": 2.0},
              dict(pthr=5.0, maxb=12, flat=False, usediv=False, bull=10.0, bear=-10.0, adev=2.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
