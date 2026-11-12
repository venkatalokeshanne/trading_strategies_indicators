"""Independent check — EB ICT Gold V5 (jrkfG0F3): 15-minute bars (24h synthetic) on a stock chart (NY day from 09:30), process_orders_on_close, one position. Sweep: low below the lowest low of the previous 10 bars and a close back above it with the sweep deeper than ATR14 x {0.45 Strict, 0.25 Balanced, 0.10 Aggressive}; rejection candle: bullish, lower wick > body x
{1.5, 1.0, 0.5}, close in the top 40 % of the range (bearish mirrored). Buy: sweep + rejection + EMA50 > EMA200 with close above EMA50 + (Strict / Balanced) EMA50 rising over 3 bars + cooldown (8 bars since the last buy signal) [+ optional daily bias from the previous day's close vs the previous day's mid (daily security, lookahead off), RSI 50-75, ADX >= 18, NY killzone 07:00-11:00]; sell: mirrored, or a
'premium sell' (bearish rejection sweep above the highest high with close above EMA50, EMA50 falling). Stop = lowest low (highest high) of the last 5 bars, target = risk x 1, placed with the entry; entry only when flat and risk > 0. Variants: default Balanced; Aggressive with RSI / ADX / daily-bias / killzone filters; Strict. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_dmi, np_ema, np_periods, np_rsi, np_security_lookahead_off, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "jrkfG0F3"


def one(df, params, mode, filt):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    pid, last_of = np_periods(df, 1440)
    npd = pid[-1] + 1
    dh = np.array([h[pid == p].max() for p in range(npd)])
    dl = np.array([l[pid == p].min() for p in range(npd)])
    dc = np.array([c[(pid == p) & last_of][0] for p in range(npd)])
    sh1 = lambda x: np.r_[np.nan, x[:-1]]
    pdh = np_security_lookahead_off(sh1(dh), pid, last_of)
    pdl = np_security_lookahead_off(sh1(dl), pid, last_of)
    pdc = np_security_lookahead_off(sh1(dc), pid, last_of)
    mid = (pdh + pdl) / 2
    ef, es = np_ema(c, 50), np_ema(c, 200)
    rsi = np_rsi(c, 14)
    adx = np_dmi(h, l, c, 14)[2]
    atr = np_atr(h, l, c, 14)
    ef3 = np.r_[np.full(3, np.nan), ef[:-3]]
    swa = {"Strict": 0.45, "Balanced": 0.25, "Aggressive": 0.10}[mode]
    wf = {"Strict": 1.5, "Balanced": 1.0, "Aggressive": 0.5}[mode]
    need_slope = mode != "Aggressive"
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    kz = (m >= 420) & (m < 660)
    liq_hi = pd.Series(np.r_[np.nan, h[:-1]]).rolling(10, min_periods=10).max().to_numpy()
    liq_lo = pd.Series(np.r_[np.nan, l[:-1]]).rolling(10, min_periods=10).min().to_numpy()
    s_lo = pd.Series(l).rolling(5, min_periods=5).min().to_numpy()
    s_hi = pd.Series(h).rolling(5, min_periods=5).max().to_numpy()
    with np.errstate(invalid="ignore"):
        bsw = (l < liq_lo) & (c > liq_lo) & ((c - l) > atr * swa)
        ssw = (h > liq_hi) & (c < liq_hi) & ((h - c) > atr * swa)
        body = np.abs(c - o)
        uw, lw, rg = h - np.fmax(o, c), np.fmin(o, c) - l, h - l
        brj = (c > o) & (lw > body * wf) & (c >= h - rg * 0.40)
        srj = (c < o) & (uw > body * wf) & (c <= l + rg * 0.40)
        sess = kz if filt else np.ones(n, bool)
        bbias = (pdc > mid) if filt else np.ones(n, bool)
        sbias = (pdc < mid) if filt else np.ones(n, bool)
        rb = ((rsi > 50) & (rsi < 75)) if filt else np.ones(n, bool)
        rs = ((rsi < 50) & (rsi > 25)) if filt else np.ones(n, bool)
        ax = (adx >= 18) if filt else np.ones(n, bool)
        sl_b = (ef > ef3) | (not need_slope)
        sl_s = (ef < ef3) | (not need_slope)
        ss_slope = ef < ef3
    S = dict(lb=None, ls=None)
    lev = {}

    def orders(i, pos):
        out = []
        bcool = S["lb"] is None or i - S["lb"] > 8
        scool = S["ls"] is None or i - S["ls"] > 8
        buy = sess[i] and bsw[i] and brj[i] and bbias[i] and rb[i] and ax[i] and sl_b[i] and bcool and c[i] > ef[i] and ef[i] > es[i]
        tsell = sess[i] and ssw[i] and srj[i] and sbias[i] and rs[i] and ax[i] and sl_s[i] and scool and c[i] < ef[i] and ef[i] < es[i]
        prem = sess[i] and ssw[i] and srj[i] and c[i] > ef[i] and c[i] < o[i] and ss_slope[i] and scool
        sell = tsell or prem
        if buy:
            S["lb"] = i
        if sell:
            S["ls"] = i
        br, sr = c[i] - s_lo[i], s_hi[i] - c[i]
        if buy and pos == 0 and br > 0:
            out.append(("entry", 1))
            lev[i] = (s_lo[i], c[i] + br * 1.0)
        if sell and pos == 0 and sr > 0:
            out.append(("entry", -1))
            lev[i] = (s_hi[i], c[i] - sr * 1.0)
        return out

    stop = lambda i, pos, ep, eb: lev[eb][0] if (eb in lev and eb < i) else None
    tgt = lambda i, pos, ep, eb: lev[eb][1] if (eb in lev and eb < i) else None
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(40000, seed=791, freq="15min")
    msgs, allok = [], True
    cases = (({}, "Balanced", False),
             ({"Entry Frequency Mode": "Aggressive", "Use Daily Bias": True, "Use RSI Momentum": True, "Use ADX Filter": True, "Trade NY Killzone Only": True}, "Aggressive", True),
             ({"Entry Frequency Mode": "Strict"}, "Strict", False))
    for params, mode, filt in cases:
        ok, m = one(df, params, mode, filt)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
