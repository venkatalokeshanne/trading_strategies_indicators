"""Independent check — PMax Explorer (nHGK4Qtp): daily bars, one unit per entry, market orders at the next open, source hl2. PMax = trailing stop of the chosen moving average +/- ATR x multiplier (long stop ratchets up while the average is above its previous value, short stop down; the direction flips when the average crosses the opposite previous stop;
the line is the long stop in an up direction and the short stop otherwise); the average crossing over / under PMax enters long / short (reversing). The moving averages are computed from their textbook formulas (SMA, EMA, WMA, TMA = SMA(SMA(ceil(n/2)), floor(n/2)+1), VAR (CMO-weighted over 9 bars), WWMA, ZLEMA, TSF = linreg + slope).
Variants: EMA defaults; VAR with length 13; ZLEMA length 9 with SMA-of-true-range ATR; TSF length 8, multiplier 2; TMA length 11; WWMA length 7; WMA length 12; SMA length 5."""
import math

import numpy as np

from indep import bars, compare, np_atr, np_ema, np_sma, np_tr, np_wma, run_conversion, simulate


TV_ID = "nHGK4Qtp"


def linreg(x, n, off):
    out = np.full(len(x), np.nan)
    xs = np.arange(n, dtype=float)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        if np.isnan(w).any():
            continue
        s, b = np.polyfit(xs, w, 1)
        out[i] = b + s * (n - 1 - off)
    return out


def get_ma(kind, src, n):
    m = len(src)
    if kind == "SMA":
        return np_sma(src, n)
    if kind == "EMA":
        return np_ema(src, n)
    if kind == "WMA":
        return np_wma(src, n)
    if kind == "TMA":
        return np_sma(np_sma(src, math.ceil(n / 2)), math.floor(n / 2) + 1)
    if kind == "VAR":
        a = 2.0 / (n + 1)
        up = np.zeros(m)
        dn = np.zeros(m)
        for i in range(1, m):
            if src[i] > src[i - 1]:
                up[i] = src[i] - src[i - 1]
            if src[i] < src[i - 1]:
                dn[i] = src[i - 1] - src[i]
        out = np.zeros(m)
        for i in range(m):
            if i >= 8:
                vu, vd = up[i - 8:i + 1].sum(), dn[i - 8:i + 1].sum()
                cmo = (vu - vd) / (vu + vd) if vu + vd != 0 else 0.0
            else:
                cmo = 0.0
            prev = out[i - 1] if i else 0.0
            out[i] = a * abs(cmo) * src[i] + (1 - a * abs(cmo)) * prev
        return out
    if kind == "WWMA":
        a = 1.0 / n
        out = np.zeros(m)
        for i in range(m):
            out[i] = a * src[i] + (1 - a) * (out[i - 1] if i else 0.0)
        return out
    if kind == "ZLEMA":
        lag = n // 2
        data = np.full(m, np.nan)
        data[lag:] = src[lag:] + (src[lag:] - src[:m - lag])
        out = np.full(m, np.nan)
        idx = np.flatnonzero(~np.isnan(data))
        s = idx[0] + n - 1
        out[s] = data[idx[0]:s + 1].mean()
        k = 2.0 / (n + 1)
        for i in range(s + 1, m):
            out[i] = k * data[i] + (1 - k) * out[i - 1]
        return out
    l0, l1 = linreg(src, n, 0), linreg(src, n, 1)
    return l0 + (l0 - l1)


def one(df, params, mav, n, mult, chg):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    m = len(c)
    src = (h + l) / 2.0
    atr = np_atr(h, l, c, 10) if chg else np_sma(np_tr(h, l, c, False), 10)
    ma = get_ma(mav, src, n)
    ls, ss, d, pm = (np.full(m, np.nan) for _ in range(4))
    dr = 1
    for i in range(m):
        lsv = ma[i] - mult * atr[i]
        lsp = ls[i - 1] if i and not np.isnan(ls[i - 1]) else lsv
        if ma[i] > lsp:
            lsv = max(lsv, lsp)
        ssv = ma[i] + mult * atr[i]
        ssp = ss[i - 1] if i and not np.isnan(ss[i - 1]) else ssv
        if ma[i] < ssp:
            ssv = min(ssv, ssp)
        if dr == -1 and ma[i] > ssp:
            dr = 1
        elif dr == 1 and ma[i] < lsp:
            dr = -1
        ls[i], ss[i] = lsv, ssv
        pm[i] = lsv if dr == 1 else ssv
    sig = []
    for i in range(m):
        if i == 0:
            sig.append(0)
            continue
        with np.errstate(invalid="ignore"):
            up = ma[i] > pm[i] and ma[i - 1] <= pm[i - 1]
            dn = ma[i] < pm[i] and ma[i - 1] >= pm[i - 1]
        sig.append(1 if up else (-1 if dn else 0))
    ref = simulate(o, h, l, c, lambda i, pos: [("entry", sig[i])] if sig[i] else [])
    ok, dd = compare(run_conversion(TV_ID, df, params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{dd} (got {len(ref)})"


def check():
    df = bars(3000, seed=44)
    msgs, allok = [], True
    cases = (({}, "EMA", 10, 3.0, True),
             ({"Moving Average Type": "VAR", "Moving Average Length": 13}, "VAR", 13, 3.0, True),
             ({"Moving Average Type": "ZLEMA", "Moving Average Length": 9, "Change ATR Calculation Method ?": False}, "ZLEMA", 9, 3.0, False),
             ({"Moving Average Type": "TSF", "Moving Average Length": 8, "ATR Multiplier": 2.0}, "TSF", 8, 2.0, True),
             ({"Moving Average Type": "TMA", "Moving Average Length": 11}, "TMA", 11, 3.0, True),
             ({"Moving Average Type": "WWMA", "Moving Average Length": 7}, "WWMA", 7, 3.0, True),
             ({"Moving Average Type": "WMA", "Moving Average Length": 12}, "WMA", 12, 3.0, True),
             ({"Moving Average Type": "SMA", "Moving Average Length": 5}, "SMA", 5, 3.0, True))
    for params, mav, n, mult, chg in cases:
        ok, msg = one(df, params, mav, n, mult, chg)
        allok &= ok
        msgs.append(msg)
    return allok, " | ".join(msgs)
