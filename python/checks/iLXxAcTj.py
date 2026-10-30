"""Independent check — Concord Execution Mandate (iLXxAcTj), 15-minute bars (24 h synthetic, UTC), orders at the bar close
(process_orders_on_close), fixed 10 units, commission / slippage 0. The efficiency-ratio dependent range filter and its locked regime,
the hand-written Wilder ADX, choppiness, the 4-hour close / EMA55 and previous-day high / low / close (lookahead on, shifted by one
period), the EMA weave and pivot geometry, the divergence block and every entry gate are rebuilt in numpy; the entries, stop / limit /
trail exit orders and the context-flip closes are replayed against the quantity-aware reference broker."""
import numpy as np

from indep import bars, compare_q, np_atr, np_ema, np_periods, np_rma, np_rsi, np_tr, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "iLXxAcTj"
QTY = 10.0
TICK = 0.01


def roll(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


def pivots(x, p, hi):
    n = len(x)
    out = np.full(n, np.nan)
    for i in range(2 * p, n):
        j = i - p
        w = x[j - p:j + p + 1]
        if (x[j] == (w.max() if hi else w.min())) and (w == x[j]).sum() == 1:
            out[i] = x[j]
    return out


def cross(a, b, up):
    pa, pb = np.r_[np.nan, a[:-1]], np.r_[np.nan, b[:-1]]
    with np.errstate(invalid="ignore"):
        return (a > b) & (pa <= pb) if up else (a < b) & (pa >= pb)


def values_when(p):
    """valuewhen(not na(p), p, k) for k = 0, 1."""
    n = len(p)
    v0, v1 = np.full(n, np.nan), np.full(n, np.nan)
    hist = []
    for i in range(n):
        if not np.isnan(p[i]):
            hist.append(p[i])
        v0[i] = hist[-1] if hist else np.nan
        v1[i] = hist[-2] if len(hist) > 1 else np.nan
    return v0, v1


def reference(df, aggressive=True, divblock=False, htf_gate=False, req_disp=True, req_reclaim=True):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    # efficiency ratio and range filter
    er_raw = np.zeros(n)
    for i in range(14, n):
        path = np.abs(np.diff(c[i - 14:i + 1])).sum()
        er_raw[i] = abs(c[i] - c[i - 14]) / path if path > 0 else 0.0
    er = np_ema(er_raw, 3)
    atr18 = np_atr(h, l, c, 18)
    filt = np.full(n, np.nan)
    trend = np.zeros(n, int)
    f, t = c[0], 0
    for i in range(n):
        em = er[i]
        mult = 1.25 * (1.15 if em < 0.25 else 0.85 if em > 0.70 else 1.0)
        buf = atr18[i] * mult
        if c[i] > f + buf:
            f = c[i] - buf
        elif c[i] < f - buf:
            f = c[i] + buf
        prev = filt[i - 1] if i else np.nan
        if f > prev:
            t = 1
        elif f < prev:
            t = -1
        filt[i], trend[i] = f, t
    confirm = np.where(er < 0.22, 4, np.where(er < 0.42, 3, np.where(er < 0.68, 2, 1)))
    confirm = np.where(np.isnan(er), 1, confirm)
    locked = np.zeros(n, int)
    lk, cand = (1 if trend[0] == 0 else trend[0]), 0
    for i in range(n):
        cand = cand + 1 if trend[i] != lk else 0
        if trend[i] != 0 and trend[i] != lk and cand >= confirm[i]:
            lk, cand = trend[i], 0
        locked[i] = lk
    # ADX (hand written in the script)
    up = np.r_[np.nan, np.diff(h)]
    dn = np.r_[np.nan, -np.diff(l)]
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr1 = np_tr(h, l, c, True)
    with np.errstate(divide="ignore", invalid="ignore"):
        pdi = 100 * np_rma(pdm, 14) / np_rma(tr1, 14)
        mdi = 100 * np_rma(mdm, 14) / np_rma(tr1, 14)
        s = pdi + mdi
        dx = np.where(s > 0, np.abs(pdi - mdi) / s * 100, 0.0)
        dx = np.where(np.isnan(s), 0.0, dx)
        adx = np_rma(dx, 14)
        csum = roll(tr1, 14, np.sum)
        rng = roll(h, 14, np.max) - roll(l, 14, np.min)
        chop = np.where(rng > 0, 100 * np.log10(csum / rng) / np.log10(14), 50.0)
    # higher timeframes (lookahead on = the period's value, which is the previous period's close / ema)
    pid, last_of = np_periods(df, 240, start_minutes=0, tz="UTC")
    hc = c[last_of]
    hema = np_ema(hc, 55)
    hclose_s = np.r_[np.nan, hc[:-1]][pid]
    hema_s = np.r_[np.nan, hema[:-1]][pid]
    with np.errstate(invalid="ignore"):
        htf_bias = np.where(hclose_s > hema_s, 1, -1)
    dpid, _ = np_periods(df, 1440, start_minutes=0, tz="UTC")
    nd = dpid.max() + 1
    dh = np.array([h[dpid == p].max() for p in range(nd)])
    dl = np.array([l[dpid == p].min() for p in range(nd)])
    dc = np.array([c[dpid == p][-1] for p in range(nd)])
    pdh, pdl, pdc = (np.r_[np.nan, a[:-1]][dpid] for a in (dh, dl, dc))
    pivot = (pdh + pdl + pdc) / 3.0
    e21, e55, e89 = np_ema(c, 21), np_ema(c, 55), np_ema(c, 89)
    wc = (e21 + e55 + e89) / 3.0
    wc2 = np.r_[[np.nan] * 2, wc[:-2]]
    with np.errstate(invalid="ignore"):
        weave = np.where((c > pivot) & (e21 > e55) & (wc > wc2), 1, np.where((c < pivot) & (e21 < e55) & (wc < wc2), -1, 0))
    ph9, pl9 = pivots(h, 9, True), pivots(l, 9, False)
    lph, rh2 = values_when(ph9)
    lpl, rl2 = values_when(pl9)
    h2, l2 = np.r_[[np.nan] * 2, h[:-2]], np.r_[[np.nan] * 2, l[:-2]]
    bfvg, sfvg = l > h2, h < l2
    sh = lambda a, k: np.r_[[False] * k, a[:-k]]
    c1 = np.r_[np.nan, c[:-1]]
    atr = atr18
    disp = (not req_disp) or True
    dispok = np.abs(c - o) >= atr * 1.0 if req_disp else np.ones(n, bool)
    with np.errstate(invalid="ignore"):
        bbos = ~np.isnan(lph) & (c > lph) & (c1 <= lph) & dispok
        sbos = ~np.isnan(lpl) & (c < lpl) & (c1 >= lpl) & dispok
        geo = np.where(~np.isnan(lpl) & ~np.isnan(rl2) & (lpl > rl2), 1,
                       np.where(~np.isnan(lph) & ~np.isnan(rh2) & (lph < rh2), -1, 0))
    basis = np_ema(c, 20)
    lrec = (not req_reclaim) or None
    long_rec = (l < basis) & (c > basis) if req_reclaim else np.ones(n, bool)
    short_rec = (h > basis) & (c < basis) if req_reclaim else np.ones(n, bool)
    # divergence block
    rsi = np_rsi(c, 14)
    dph, dpl = pivots(h, 3, True), pivots(l, 3, False)
    bear_div_bar = np.full(n, np.nan)
    bull_div_bar = np.full(n, np.nan)
    pa = pb = None
    last_bear = last_bull = np.nan
    for i in range(n):
        if not np.isnan(dph[i]):
            cb = i - 3
            if pa is not None and cb - pa[2] <= 50 and dph[i] > pa[0] and rsi[i - 3] < pa[1]:
                last_bear = cb
            pa = (dph[i], rsi[i - 3], cb)
        if not np.isnan(dpl[i]):
            cb = i - 3
            if pb is not None and cb - pb[2] <= 50 and dpl[i] < pb[0] and rsi[i - 3] > pb[1]:
                last_bull = cb
            pb = (dpl[i], rsi[i - 3], cb)
        bear_div_bar[i], bull_div_bar[i] = last_bear, last_bull
    idx = np.arange(n)
    bear_blk = ~np.isnan(bear_div_bar) & ((idx - bear_div_bar) <= 20)
    bull_blk = ~np.isnan(bull_div_bar) & ((idx - bull_div_bar) <= 20)
    xfu, xfd = cross(c, filt, True), cross(c, filt, False)
    xpu, xpd = cross(c, pivot, True), cross(c, pivot, False)
    xbu, xbd = cross(c, basis, True), cross(c, basis, False)
    xeu, xed = cross(c, e21, True), cross(c, e21, False)
    bcont = (locked == 1) & xfu & (c > pivot) & (c > basis)
    scont = (locked == -1) & xfd & (c < pivot) & (c < basis)
    brot = aggressive & ((locked == 1) | (c > filt)) & (xpu | xbu | xeu)
    srot = aggressive & ((locked == -1) | (c < filt)) & (xpd | xbd | xed)
    ltrig = (bbos & (bfvg | sh(bfvg, 1) | sh(bfvg, 2))) | bcont | brot
    strig = (sbos & (sfvg | sh(sfvg, 1) | sh(sfvg, 2))) | scont | srot
    lal = (weave >= 0).astype(int) + (geo >= 0) + (c > filt) + (c > pivot)
    sal = (weave <= 0).astype(int) + (geo <= 0) + (c < filt) + (c < pivot)
    qual = (adx >= 18).astype(int) + (chop <= 61.8) + (htf_bias == locked)
    soft = ((qual >= 1) | aggressive) & ((not htf_gate) | (htf_bias == locked))
    lctx = (locked == 1) | (c > filt) | (e21 > e55)
    sctx = (locked == -1) | (c < filt) | (e21 < e55)
    with np.errstate(invalid="ignore"):
        long_stack = lctx & soft & ltrig & (long_rec | brot | bcont) & (lal >= 1) & ((not divblock) | ~bear_blk)
        short_stack = sctx & soft & strig & (short_rec | srot | scont) & (sal >= 1) & ((not divblock) | ~bull_blk)
    lsb = np.fmin(np.where(np.isnan(lpl), c - atr * 1.6, lpl), c - atr * 1.6)
    ssb = np.fmax(np.where(np.isnan(lph), c + atr * 1.6, lph), c + atr * 1.6)

    def orders(i, info):
        out = []
        pos, avg = info["pos"], info["avg"]
        if long_stack[i] and pos <= 0:
            out.append(("entry", "Long", 1, QTY))
        if short_stack[i] and pos >= 0:
            out.append(("entry", "Short", -1, QTY))
        if pos > 0:
            risk = max(avg - lsb[i], TICK)
            tgt = avg + risk * 2.2
            stop = max(lsb[i], c[i] - atr[i] * 1.2) if h[i] >= avg + risk * 1.0 else lsb[i]
            out.append(("exit", "Long Exit", "Long", None, stop, tgt))
        if pos < 0:
            risk = max(ssb[i] - avg, TICK)
            tgt = avg - risk * 2.2
            stop = min(ssb[i], c[i] + atr[i] * 1.2) if l[i] <= avg - risk * 1.0 else ssb[i]
            out.append(("exit", "Short Exit", "Short", None, stop, tgt))
        if pos > 0 and (locked[i] == -1 or weave[i] == -1):
            out.append(("close", "Long"))
        if pos < 0 and (locked[i] == 1 or weave[i] == 1):
            out.append(("close", "Short"))
        return out

    return simulate_brackets(o, h, l, c, orders, pyramiding=1, on_close=True, tick=TICK, qty_step=1e-9)


def check():
    df = bars(30000, seed=35, freq="15min")
    lc = np.log(df["close"].to_numpy() / 100)
    det = lc - np.polyval(np.polyfit(np.arange(len(lc)), lc, 1), np.arange(len(lc)))
    rel = {k: df[k].to_numpy() / df["close"].to_numpy() for k in ("open", "high", "low", "close")}
    for k in rel:
        df[k] = 100 * np.exp(0.5 * det) * rel[k] ** 0.5
    sym = SymbolInfo.make("BINANCE:BTCUSDT", "crypto", qty_step=1e-9)
    ov = {"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}
    cases = (({}, {}),
             ({"Allow Aggressive Rotation Entries": False, "Use HTF As Hard Gate": True, "Use Divergence Block Filter": True},
              dict(aggressive=False, htf_gate=True, divblock=True)),
             ({"Require Displacement With Break": False, "Require Intrabar Reclaim": False}, dict(req_disp=False, req_reclaim=False)))
    msgs, ok_all = [], True
    for params, kw in cases:
        ref = reference(df, **kw)
        ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides=ov), ref)
        ok_all = ok_all and ok and len(ref) > 12
        msgs.append(f"{d} (got {len(ref)})")
    return ok_all, " | ".join(msgs)
