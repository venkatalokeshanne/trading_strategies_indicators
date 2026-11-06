"""Independent check — ULTIMATE TEMA/LSMA + IDEAL + REVERSAL (57hl5yBd): 5-minute bars (24 h synthetic, price ~100) of a stock-style symbol, orders at the signal bar's close (process_orders_on_close), the default 10 % of equity quantity (equity mirrored from the closed trades), commission / slippage / margin off.
Every indicator (TEMA, linear regression, EMA100, ATR, RSI, MACD, DMI / ADX, EMA-based KAMA, stochastic, stochastic RSI, Williams %R, CCI, pivots) and the signal cascade (IDEAL sweeps / retests / oversold confluence, reversal consensus, TEMA / LSMA cross with the trend-exhaustion state) is restated bar by bar; the exit order (ATR stop / target, trailing stop of half the ATR in ticks) is re-issued every bar and a trade older than the maximum bars is closed.
Uses the quantity-aware bracket reference (indep.simulate_brackets, on_close). Variants: defaults; IDEAL off (0.0001 tick); IDEAL, reversals, alignment and exhaustion off on a bitcoin-named symbol; divergence off on a gold-named symbol."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_cross_over, np_cross_under, np_ema, np_rma, np_rsi, np_sma, np_tr, np_vwap, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "57hl5yBd"


def sma_prefix(x, n):
    out = np.full(len(x), np.nan)
    psum = [0.0]
    pnan = [0]
    for i, v in enumerate(x):
        m = i
        if m + 1 >= n and not np.isnan(v) and pnan[m] - pnan[m - (n - 1)] == 0:
            out[i] = (psum[m] - psum[m - (n - 1)] + v) / n
        psum.append(psum[-1] + (0.0 if np.isnan(v) else v))
        pnan.append(pnan[-1] + (1 if np.isnan(v) else 0))
    return out


def wfn(x, n, fn):
    """Rolling highest / lowest: full window of n bars, na values ignored."""
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        w = w[~np.isnan(w)]
        if len(w):
            out[i] = fn(w)
    return out


def stoch(c, h, l, n):
    hh, ll = wfn(h, n, np.max), wfn(l, n, np.min)
    with np.errstate(divide="ignore", invalid="ignore"):
        k = 100 * (c - ll) / (hh - ll)
    k[~np.isfinite(k)] = np.nan
    return k


def linreg(y, n):
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
        out[i] = (sy - slope * sx) / n + slope * (n - 1)
    return out


def dev(x, n):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        if not np.isnan(w).any():
            out[i] = np.abs(w - w.mean()).mean()
    return out


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


def sdiv(a, b):
    return np.nan if (b == 0 or np.isnan(a) or np.isnan(b)) else a / b


def rq(q, step=1e-9):
    n = q / step
    return np.floor(n + max(1e-9, abs(n) * 1e-12)) * step


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    tick = p["tick"]
    nm = p["name"]
    kind = "GOLD" if ("GC" in nm or "GOLD" in nm) else "BITCOIN" if "BTC" in nm else "OTHER"
    pv_look = 5 if kind == "GOLD" else 10 if kind == "BITCOIN" else 5
    sweep_atr = 0.3 if kind == "GOLD" else 0.5 if kind == "BITCOIN" else 0.3
    retest_tol = 0.001 if kind == "GOLD" else 0.005 if kind == "BITCOIN" else 0.001
    atr_test = 0.2 if kind == "GOLD" else 0.5 if kind == "BITCOIN" else 0.2
    zt1 = {"GOLD": 2.0, "BITCOIN": 5.0, "OTHER": 2.0}[kind]
    zt2 = {"GOLD": 1.0, "BITCOIN": 2.5, "OTHER": 1.0}[kind]

    lsma = linreg(c, 25)
    x1 = np_ema(c, 9)
    x2 = np_ema(x1, 9)
    x3 = np_ema(x2, 9)
    tema = 3 * x1 - 3 * x2 + x3
    ema100 = np_ema(c, 100)
    atr = np_atr(h, l, c, 14)
    rsi = np_rsi(c, 14)
    vma = np_sma(v, 20)
    vw = np_vwap(df, c)
    ma200, ma10 = np_sma(c, 200), np_sma(c, 10)
    hi52 = wfn(h, 52, np.max)
    swh, swl = wfn(h, 20, np.max), wfn(l, 20, np.min)
    k_ = sma_prefix(stoch(c, h, l, 9), 6)
    d_ = sma_prefix(k_, 3)
    r_lo, r_hi = wfn(rsi, 14, np.min), wfn(rsi, 14, np.max)
    with np.errstate(divide="ignore", invalid="ignore"):
        srsi = np.where((r_hi - r_lo) == 0, np.nan, (rsi - r_lo) / (r_hi - r_lo) * 100)
    macd = np_ema(c, 12) - np_ema(c, 26)
    sig = np_ema(macd, 9)
    ch_h = np.r_[np.nan, np.diff(h)]
    ch_l = np.r_[np.nan, np.diff(l)]
    dmp = np_rma(np.where(np.isnan(ch_h), np.nan, np.maximum(ch_h, 0)), 14)
    dmm = np_rma(np.where(np.isnan(ch_l), np.nan, -np.minimum(ch_l, 0)), 14)
    trur = np_rma(np_tr(h, l, c, False), 14)
    pdi = np.array([100 * sdiv(a, b) for a, b in zip(dmp, trur)])
    mdi = np.array([100 * sdiv(a, b) for a, b in zip(dmm, trur)])
    dx = np.array([100 * sdiv(abs(a - b), a + b) for a, b in zip(pdi, mdi)])
    adx = np_rma(dx, 14)
    hh14, ll14 = wfn(h, 14, np.max), wfn(l, 14, np.min)
    will = np.array([-100 * sdiv(a - cc, a - b) for a, b, cc in zip(hh14, ll14, c)])
    sma14 = np_sma(c, 14)
    dv14 = dev(c, 14)
    cci = np.array([sdiv(cc - s, 0.015 * dd) for cc, s, dd in zip(c, sma14, dv14)])
    kama = np_ema(c, 10)
    ph, pl = pivots(h, pv_look, pv_look, True), pivots(l, pv_look, pv_look, False)
    xup_e, xdn_e = np_cross_over(c, ema100), np_cross_under(c, ema100)
    x_up, x_dn = np_cross_over(tema, lsma), np_cross_under(tema, lsma)

    log: list = []
    S = dict(lph=np.nan, lpl=np.nan, lbb=np.nan, lsb=np.nan, tcnt=0, ltp=np.nan, tbi=None, tb=0, tbull=False, tsp=0.0, dbc=False, dbp=0.0, src={})

    def orders(i, info):
        pos = info["pos"]
        out = []
        eq = 1_000_000.0 + sum(d * (xp - ep) * q for d, _, ep, _, xp, q in log)
        a = atr[i]
        if ph[i]:
            S["lph"] = h[i - pv_look]
        if pl[i]:
            S["lpl"] = l[i - pv_look]
        lph, lpl = S["lph"], S["lpl"]
        h1 = h[i - 1] if i > 0 else np.nan
        l1 = l[i - 1] if i > 0 else np.nan
        with np.errstate(invalid="ignore"):
            hi_ch = (hi52[i] - c[i]) / hi52[i] * 100
            dbc = bool(p["davin"] and ((c[i] > ma200[i] and c[i] < ma10[i] and pos == 0) or (pos == 0 and hi_ch > 14)))
            dsell = bool(p["davin"] and (c[i] > ma10[i] and pos > 0 and (c[i] < l1 or np.isnan(l1) and False)))
            dsd = (S["dbp"] - c[i]) / c[i] if pos > 0 else np.nan
            dstop = bool(pos > 0 and dsd > 0.15)
            buy_lo, buy_hi = swl[i], swl[i] + a * 0.5
            sell_hi, sell_lo = swh[i], swh[i] - a * 0.5
            mid = vw[i]
            mid_lo, mid_hi = mid - a * 0.25, mid + a * 0.25
            rng = a * 0.5
            bear = int(rsi[i] < 50) + int(k_[i] < 50 or k_[i] < d_[i]) + int(srsi[i] < 50) + int(macd[i] < sig[i]) + int(will[i] < -50) + int(cci[i] < 0)
            bull = int(rsi[i] > 50) + int(k_[i] > 50 or k_[i] > d_[i]) + int(srsi[i] > 50) + int(macd[i] > sig[i]) + int(will[i] > -50) + int(cci[i] > 0)
            kr = i > 0 and kama[i] > kama[i - 1]
            kf = i > 0 and kama[i] < kama[i - 1]
            ltr = c[i] > kama[i] and kr and (adx[i] > 20 or pdi[i] > mdi[i])
            str_ = c[i] < kama[i] and kf and (adx[i] > 20 or mdi[i] > pdi[i])
            vok_rev = v[i] > vma[i] * 1.0
            vok = v[i] > vma[i] * 1.2
            msz = a * sweep_atr
            sw_dn = l[i] < lpl and c[i] > h1 and (h1 - l[i]) > msz
            sw_up = h[i] > lph and c[i] < l1 and (h[i] - l1) > msz
            bb = bool(xup_e[i] and c[i] > ema100[i])
            sb = bool(xdn_e[i] and c[i] < ema100[i])
            if bb:
                S["lbb"] = ema100[i]
            if sb:
                S["lsb"] = ema100[i]
            lbb, lsb = S["lbb"], S["lsb"]
            b_rt = (not np.isnan(lbb)) and c[i] < lbb * (1 + retest_tol) and c[i] > lbb * (1 - retest_tol) and c[i] > o[i]
            s_rt = (not np.isnan(lsb)) and c[i] > lsb * (1 - retest_tol) and c[i] < lsb * (1 + retest_tol) and c[i] < o[i]
            if abs(c[i] - ema100[i]) < a * atr_test:
                if np.isnan(S["ltp"]) or (i != S["tbi"] and S["ltp"] != c[i]):
                    S["tcnt"] += 1
                    S["ltp"] = c[i]
                    S["tbi"] = i
            if abs(c[i] - ema100[i]) > a * 0.5:
                S["tcnt"] = 0
            lower_high = h[i] < lph and h[i] > h1
            zs = ((c[i] - tema[i]) / tema[i] * 100 + (c[i] - lsma[i]) / lsma[i] * 100 + (c[i] - ema100[i]) / ema100[i] * 100) / 3
            if zs <= -zt1:
                zone = "EXTREME_OVERSOLD"
            elif zs <= -zt2:
                zone = "OVERSOLD"
            elif zs <= 0.5:
                zone = "NEUTRAL_LOW"
            elif zs <= 1.5:
                zone = "NEUTRAL_HIGH"
            elif zs <= zt2:
                zone = "OVERBOUGHT"
            else:
                zone = "EXTREME_OVERBOUGHT"
            tb_ = i > 0 and tema[i] > tema[i - 1]
            lb_ = i > 0 and lsma[i] > lsma[i - 1]
            eb_ = i > 0 and ema100[i] > ema100[i - 1]
            allbull = tb_ and lb_ and eb_
            allbear = (not tb_) and (not lb_) and (not eb_)
            if p["align"]:
                lal, sal = allbull, allbear
            else:
                lal = bool(tema[i] > lsma[i] and c[i] > ema100[i])
                sal = bool(tema[i] < lsma[i] and c[i] < ema100[i])
            t5 = tema[i - 5] if i >= 5 else np.nan
            l10 = lsma[i - 10] if i >= 10 else np.nan
            e20 = ema100[i - 20] if i >= 20 else np.nan
            nstr = sdiv(abs(((tema[i] - t5) + (lsma[i] - l10) + (ema100[i] - e20)) / 3), a)
        if i == 0:
            S["tb"], S["tbull"], S["tsp"] = 0, False, 0.0
        else:
            if allbull and ((not S["tbull"]) or S["tsp"] == 0.0):
                S["tb"], S["tbull"], S["tsp"] = 1, True, c[i]
            elif allbear and (S["tbull"] or S["tsp"] == 0.0):
                S["tb"], S["tbull"], S["tsp"] = 1, False, c[i]
            elif (S["tbull"] and allbull) or ((not S["tbull"]) and allbear):
                S["tb"] += 1
            else:
                S["tb"], S["tbull"], S["tsp"] = 0, False, 0.0
        exh = False
        with np.errstate(invalid="ignore"):
            if S["tb"] > 0 and S["tsp"] > 0.0:
                c1 = S["tb"] > 20
                c2 = nstr < 0.5
                c3 = (S["tbull"] and not allbull) or ((not S["tbull"]) and not allbear)
                rd = False
                if p["div"]:
                    if S["tbull"]:
                        rd = bool(i >= 10 and c[i] > c[i - 10] and rsi[i] < rsi[i - 10])
                    else:
                        rd = bool(i >= 10 and c[i] < c[i - 10] and rsi[i] > rsi[i - 10])
                exh = c1 and (c2 or c3 or rd)
            rev_l = bool(p["rev"] and ltr and bull >= 3 and vok_rev)
            rev_s = bool(p["rev"] and str_ and bear >= 3 and vok_rev)
            act = "WAIT"
            if p["ideal"]:
                if sw_dn and c[i] > ema100[i] and vok:
                    act = "BUY"
                elif b_rt and tema[i] > lsma[i] and vok:
                    act = "BUY"
                elif zone in ("EXTREME_OVERSOLD", "OVERSOLD") and c[i] > ema100[i] and tema[i] > lsma[i] and vok:
                    act = "BUY"
                if s_rt and tema[i] < lsma[i] and vok:
                    act = "SELL"
                elif lower_high and zone in ("OVERBOUGHT", "EXTREME_OVERBOUGHT") and tema[i] < lsma[i]:
                    act = "SELL"
                elif S["tcnt"] >= 3 and c[i] < ema100[i] and tema[i] < lsma[i] and xdn_e[i]:
                    act = "SELL"
            inst_act = "WAIT"
            inst_sz = 10.0
            if c[i] >= buy_lo and c[i] <= buy_hi:
                inst_act = "ACCUMULATE"
                inst_sz = 10.0 * (1 + (buy_hi - c[i]) / rng) if rng > 0 else 10.0
            elif c[i] >= sell_lo and c[i] <= sell_hi:
                inst_act = "DISTRIBUTE"
                inst_sz = 10.0 * (1 + (c[i] - sell_lo) / rng) if rng > 0 else 10.0
            elif c[i] >= mid_lo and c[i] <= mid_hi:
                inst_act = "PROVIDE_LIQUIDITY"
            il = bool(p["inst"] and inst_act == "ACCUMULATE")
            is_ = bool(p["inst"] and inst_act == "DISTRIBUTE")
            dl = bool(p["davin"] and dbc)
            ds = bool(p["davin"] and (dsell or dstop))
            vok_x = v[i] > vma[i] * 1.2
            tup, tdn = bool(x_up[i]), bool(x_dn[i])
        lc = sc = False
        if p["inst"] and il:
            lc, src = True, "INSTITUTIONAL"
        elif p["inst"] and is_:
            sc, src = True, "INSTITUTIONAL"
        elif p["ideal"] and act == "BUY" and pos == 0:
            lc, src = True, "IDEAL"
        elif p["ideal"] and act == "SELL" and pos == 0:
            sc, src = True, "IDEAL"
        elif p["rev"] and rev_l and pos == 0:
            lc, src = True, "REVERSAL"
        elif p["rev"] and rev_s and pos == 0:
            sc, src = True, "REVERSAL"
        elif p["davin"] and dl and pos == 0:
            lc, src = True, "DAVIN MA"
        elif p["davin"] and ds and pos > 0:
            sc, src = True, "DAVIN MA"
        else:
            if p["exh"]:
                lc = (lal and tup and vok_x) or (exh and not S["tbull"] and tup and vok_x)
                sc = (sal and tdn and vok_x) or (exh and S["tbull"] and tdn and vok_x)
            else:
                lc = lal and tup and vok_x
                sc = sal and tdn and vok_x
            src = "ORIGINAL" if (lc or sc) else ""
        if p["davin"] and S["dbc"]:
            S["dbp"] = o[i]
        S["dbc"] = dbc
        S["src"][src] = S["src"].get(src, 0) + int((lc or sc) and pos == 0)
        avg = info["avg"]
        tr_off = a * 0.5
        if pos != 0:
            m1, m2 = (1.5, 1.2) if src == "INSTITUTIONAL" else (1.0, 1.0)
            if pos > 0:
                sl, tp = avg - 1.5 * m1 * a, avg + 3.0 * m2 * a
            else:
                sl, tp = avg + 1.5 * m1 * a, avg - 3.0 * m2 * a
        psz = 10.0
        if lc and pos == 0:
            out.append(("entry", "Long", 1, rq(eq / c[i] * psz / 100)))
        if sc and pos == 0:
            out.append(("entry", "Short", -1, rq(eq / c[i] * psz / 100)))
        if pos > 0:
            out.append(("exit", "Long Exit", "Long", None, sl, tp, tr_off, None, tr_off))
        if pos < 0:
            out.append(("exit", "Short Exit", "Short", None, sl, tp, tr_off, None, tr_off))
        if pos != 0 and i - info["lots"][0]["eb"] >= 25:
            out.append(("close_all",))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, on_close=True, tick=tick, qty_step=1e-9, log=log)
    sym = SymbolInfo.make("NASDAQ:" + nm, "stock", mintick=tick, qty_step=1e-9)
    ov = {"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides=ov), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)}; {S['src']})"


BASE = dict(inst=False, ideal=True, rev=True, davin=False, align=True, exh=True, div=True, tick=0.01, name="XYZ")


def check():
    df = bars(30000, seed=829, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.1
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Use IDEAL Conditions (Priority)": False}, dict(ideal=False, tick=0.0001)),
             ({"Use IDEAL Conditions (Priority)": False, "Enable Reversal Trades?": False, "Require All Indicators Aligned": False, "Use Trend Exhaustion Filter": False},
              dict(ideal=False, rev=False, align=False, exh=False, tick=0.0001, name="BTCUSDT")),
             ({"Use Momentum Divergence": False}, dict(div=False, tick=0.0001, name="GOLDX")))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
