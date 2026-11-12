"""Independent check — MASU+ Fib [BTT] (QCkIgf3z): 15-minute bars (24 h synthetic, price ~100) of a stock-style symbol, market orders at the next open, fixed quantity (the percent-of-equity sizing is replaced), commission / slippage / margin off.
Restated bar by bar: 21/50/200 EMAs, ADX(14), Bollinger(20, 2), RSI(14), 20-bar volume spike, 20-bar breakout levels (previous bar's), the 8-MA ribbon (EMA / SMA / HMA) alignment count, the 240-minute EMA filter (lookahead off), the daily-reset VWAP, the cumulative volume delta vs its average, the Fibonacci swing / retracement-touch logic, the trading session, and the trend / breakout / mean-reversion entries gated by all filters. A flat strategy enters and attaches the exit order in the same bar: ATR stop with an ATR trailing stop (ticks) or with an ATR target.
Uses the quantity-aware bracket reference (indep.simulate_brackets). Variants: defaults; HMA ribbon without trailing (stop + target); ribbon / MTF / order-flow / Fibonacci / session filters off with a 3-bar ribbon threshold of 4."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_cross_over, np_cross_under, np_dmi, np_ema, np_periods, np_rsi, np_security_lookahead_off, np_sma, np_wma, np_vwap, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "QCkIgf3z"
QTY = 10.0


def wfn(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


def hma(x, n):
    a, b = np_wma(x, int(n / 2)), np_wma(x, n)
    return np_wma(2 * a - b, int(np.floor(np.sqrt(n) + 0.5)))


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    loc = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (loc.dt.hour * 60 + loc.dt.minute).to_numpy()
    sess = (mins >= 9 * 60) & (mins < 22 * 60) if p["sess"] else np.full(n, True)
    atr = np_atr(h, l, c, 14)
    ef, es, et = np_ema(c, 21), np_ema(c, 50), np_ema(c, 200)
    _, _, adx = np_dmi(h, l, c, 14)
    basis = np_sma(c, 20)
    dev = np.array([np.std(c[i - 19:i + 1]) if i >= 19 else np.nan for i in range(n)])
    bbu, bbl = basis + 2.0 * dev, basis - 2.0 * dev
    rsi = np_rsi(c, 14)
    vsma = np_sma(v, 20)
    spike = v > vsma * 1.2
    hh, ll = wfn(h, 20, np.max), wfn(l, 20, np.min)
    mk = {"EMA": np_ema, "SMA": np_sma, "HMA": hma}[p["ribbon_type"]]
    r = [mk(c, k) for k in (8, 13, 21, 34, 55, 89, 144, 233)]
    pid, last_of = np_periods(df, 240)
    cc = pd.Series(c).groupby(pid).last().to_numpy()
    mf = np_security_lookahead_off(np_ema(cc, 21), pid, last_of)
    ms = np_security_lookahead_off(np_ema(cc, 55), pid, last_of)
    mc = np_security_lookahead_off(cc, pid, last_of)
    day, _ = np_periods(df, 1440)
    vwap = np_vwap(df, (h + l + c) / 3)   # volume-weighted hlc3 per session day, reset like the script's time('D') change
    cvd = np.cumsum(np.where(c > o, v, 0.0) - np.where(c < o, v, 0.0))
    cvd_sma = np_sma(cvd, 20)
    xu_e, xd_e = np_cross_over(ef, es), np_cross_under(ef, es)
    xu_r, xd_r = np_cross_over(rsi, 30), np_cross_under(rsi, 70)
    xu_v, xd_v = np_cross_over(c, vwap), np_cross_under(c, vwap)
    S = dict(swH=np.nan, swHb=0, swL=np.nan, swLb=0)
    rng_hi, rng_lo = wfn(h, 16, np.max), wfn(l, 16, np.min)

    def orders(i, info):
        out = []
        a = atr[i]
        with np.errstate(invalid="ignore"):
            bull_n = sum(r[k][i] > r[k + 1][i] for k in range(7))
            bear_n = sum(r[k][i] < r[k + 1][i] for k in range(7))
            rb_l = (not p["ribbon"]) or bull_n >= p["thr"] - 1
            rb_s = (not p["ribbon"]) or bear_n >= p["thr"] - 1
            mb = bool(mf[i] > ms[i] and mc[i] > mf[i])
            mr = bool(mf[i] < ms[i] and mc[i] < mf[i])
            mtf_l, mtf_s = (not p["mtf"]) or mb, (not p["mtf"]) or mr
            buy = v[i] if c[i] > o[i] else 0.0
            sell = v[i] if c[i] < o[i] else 0.0
            cprev = c[i - 1] if i > 0 else np.nan
            cv_b = bool(cvd[i] > cvd_sma[i] and c[i] < cprev and i > 0 and cvd[i] > cvd[i - 1])
            cv_s = bool(cvd[i] < cvd_sma[i] and c[i] > cprev and i > 0 and cvd[i] < cvd[i - 1])
            ratio = buy / max(sell, 1)
            above, below = bool(c[i] > vwap[i]), bool(c[i] < vwap[i])
            of_b = p["of"] and ((cv_b or ratio > 1.6) and (bool(xu_v[i]) or above))
            of_s = p["of"] and ((cv_s or ratio < 0.4) and (bool(xd_v[i]) or below))
            of_l = (not p["of"]) or of_b or above
            of_sh = (not p["of"]) or of_s or below
        is_sh = bool(h[i] == rng_hi[i])
        is_sl = bool(l[i] == rng_lo[i])
        with np.errstate(invalid="ignore"):
            if is_sh and (h[i] - rng_lo[i]) >= 1.0 * a:
                S["swH"], S["swHb"] = h[i], i
            if is_sl and (rng_hi[i] - l[i]) >= 1.0 * a:
                S["swL"], S["swLb"] = l[i], i
            swH, swL = S["swH"], S["swL"]
            ok = (not np.isnan(swH)) and (not np.isnan(swL)) and S["swHb"] > 0 and S["swLb"] > 0
            diff = swH - swL if ok else 0.0
            up = ok and S["swHb"] > S["swLb"]
            f = [swH - q * diff if ok else np.nan for q in (0.382, 0.5, 0.618)]
            cr = h[i] - l[i]
            bw = (min(o[i], c[i]) - l[i]) / cr if cr > 0 else 0.0
            sw = (h[i] - max(o[i], c[i])) / cr if cr > 0 else 0.0
            fz = 0.6 * a
            old = ok and i - S["swHb"] >= 2 and i - S["swLb"] >= 2
            tl = [up and not np.isnan(f[k]) and abs(l[i] - f[k]) <= fz for k in range(3)]
            ts = [(not up) and not np.isnan(f[k]) and abs(h[i] - f[k]) <= fz for k in range(3)]
            nl = f[0] if tl[0] else f[1] if tl[1] else f[2]
            ns = f[0] if ts[0] else f[1] if ts[1] else f[2]
            bounce = bw >= 0.25 or (c[i] > o[i] and c[i] > nl)
            reject = sw >= 0.25 or (c[i] < o[i] and c[i] < ns)
            fb = p["fib"] and old and any(tl) and bounce
            fs = p["fib"] and old and any(ts) and reject
            fib_l = (not p["fib"]) or fb or up
            fib_s = (not p["fib"]) or fs or (not up)
            trending, ranging = adx[i] > 20, adx[i] <= 20
            hh1 = hh[i - 1] if i > 0 else np.nan
            ll1 = ll[i - 1] if i > 0 else np.nan
            tl_ = trending and (ef[i] > es[i] and c[i] > et[i]) and xu_e[i] and spike[i]
            ts_ = trending and (ef[i] < es[i] and c[i] < et[i]) and xd_e[i] and spike[i]
            bl = c[i] > hh1 and spike[i] and c[i] > et[i]
            bs = c[i] < ll1 and spike[i] and c[i] < et[i]
            ml = ranging and c[i] < bbl[i] and rsi[i] < 30 and xu_r[i]
            ms_ = ranging and c[i] > bbu[i] and rsi[i] > 70 and xd_r[i]
            lc = bool((tl_ or bl or ml) and mtf_l and rb_l and of_l and fib_l and sess[i])
            sc = bool((ts_ or bs or ms_) and mtf_s and rb_s and of_sh and fib_s and sess[i])
        flat = info["pos"] == 0
        if lc and flat:
            sl, tp = c[i] - a * 2.0, c[i] + a * 3.0
            out.append(("entry", "Long", 1, QTY))
            out.append(("exit", "Exit Long", "Long", None, sl, None, a * 1.5, None, a * 1.5) if p["trail"] else ("exit", "Exit Long", "Long", None, sl, tp))
        if sc and flat:
            sl, tp = c[i] + a * 2.0, c[i] - a * 3.0
            out.append(("entry", "Short", -1, QTY))
            out.append(("exit", "Exit Short", "Short", None, sl, None, a * 1.5, None, a * 1.5) if p["trail"] else ("exit", "Exit Short", "Short", None, sl, tp))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=0.01, qty_step=1e-9)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ov = {"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides=ov), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(ribbon_type="EMA", trail=True, ribbon=True, thr=6, mtf=True, of=True, fib=True, sess=True)


def check():
    df = bars(40000, seed=611, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.1
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Ribbon MA Type": "HMA", "Use Trailing Stop": False}, dict(ribbon_type="HMA", trail=False)),
             ({"Use MA Ribbon": False, "Use MTF Filter": False, "Enable Order Flow Analysis": False, "Enable Fibonacci": False, "Trade Only During Session": False, "Ribbon Alignment Threshold": 4},
              dict(ribbon=False, mtf=False, of=False, fib=False, sess=False, thr=4)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
