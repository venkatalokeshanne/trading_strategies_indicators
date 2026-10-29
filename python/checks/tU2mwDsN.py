"""Independent check — FLI + STC + MACD + EMA Strategy v1 (tU2mwDsN, same script as xlNwG5Ho): daily bars, market orders at the next open, one position, risk-sized (the quantity does not change the trade list). Follow Line: Bollinger (21, 1 sd) signal moves an ATR(5)-offset trend line (bull: max(low - ATR, line), bear: min(high + ATR, line), else unchanged; the trend flips with the line's direction). Confirmations counted: STC (MACD 26/50 stochastic-of-stochastic over 12 bars, smoothed 0.5; modes turn-from-zone / threshold cross / slope / any), MACD (12, 26, 9; cross / slope / combos; EMA or SMA types; optional zero-line filter) and price vs EMA200 (side / cross / slope / any); entry modes Loose (1), Balanced (2), Strict (all). Bracket = ATR14 x 1.5 stop and x 3 target, or the fixed-points risk:reward, or the stop alone (the source's trail offset has no activation level so never trails), or no bracket with an exit on the opposite flip. Commission / slippage / margin off on the pinelib side.
Variants: defaults; Loose + fixed RR + 'any' modes + MACD cross-and-slope; Strict + FLI flip exit + slope modes + SMA MACD; Trailing + threshold-cross STC + cross-EMA + cross-only MACD with the zero filter."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_sma, run_conversion, simulate

TV_ID = "tU2mwDsN"


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


def lowest(x, n):
    return np.array([np.nanmin(x[i - n + 1:i + 1]) if i >= n - 1 and not np.all(np.isnan(x[i - n + 1:i + 1])) else np.nan for i in range(len(x))])


def highest(x, n):
    return np.array([np.nanmax(x[i - n + 1:i + 1]) if i >= n - 1 and not np.all(np.isnan(x[i - n + 1:i + 1])) else np.nan for i in range(len(x))])


def cross(a, b, up=True):
    pa, pb = np.r_[np.nan, a[:-1]], np.r_[np.nan, b[:-1]]
    with np.errstate(invalid="ignore"):
        return ((a > b) & (pa <= pb)) if up else ((a < b) & (pa >= pb))


def one(df, params, mode, method, stcm, emam, macdm, macd_sma, zero):
    import warnings
    warnings.simplefilter("ignore")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sh = lambda x, k=1: np.r_[np.full(k, np.nan), x[:-k]]
    # Follow line
    basis = np_sma(c, 21)
    dev = pd.Series(c).rolling(21).std(ddof=0).to_numpy()
    sig = np.where(c > basis + dev, 1, np.where(c < basis - dev, -1, 0))
    fatr = np_atr(h, l, c, 5)
    tl = np.full(n, np.nan)
    trend = np.zeros(n)
    tl[0] = c[0]
    for i in range(1, n):
        prev = tl[i - 1]
        if sig[i] == 1:
            cand = l[i] - fatr[i]
            tl[i] = np.nan if np.isnan(cand) else max(cand, cand if np.isnan(prev) else prev)
        elif sig[i] == -1:
            cand = h[i] + fatr[i]
            tl[i] = np.nan if np.isnan(cand) else min(cand, cand if np.isnan(prev) else prev)
        else:
            tl[i] = c[i] if np.isnan(prev) else prev
    for i in range(n):
        pt = trend[i - 1] if i else 0
        p = tl[i - 1] if i else np.nan
        pn = tl[i] if np.isnan(p) else p
        trend[i] = 1 if tl[i] > pn else (-1 if tl[i] < pn else pt)
    ptr = sh(trend)
    bflip = (np.nan_to_num(ptr) == -1) & (trend == 1)
    sflip = (np.nan_to_num(ptr) == 1) & (trend == -1)
    # EMA
    e200 = np_ema(c, 200)
    pe = sh(e200)
    with np.errstate(invalid="ignore"):
        up_, dn_ = e200 > pe, e200 < pe
        xu, xd = cross(c, e200, True), cross(c, e200, False)
        if emam == "price":
            eb, es = c > e200, c < e200
        elif emam == "cross":
            eb, es = xu, xd
        elif emam == "slope":
            eb, es = up_, dn_
        else:
            eb, es = (c > e200) | xu | up_, (c < e200) | xd | dn_
    # STC
    macd = np_ema(c, 26) - np_ema(c, 50)
    lo_m, hi_m = lowest(macd, 12), highest(macd, 12)
    k1, d1, k2, stc = np.zeros(n), np.full(n, np.nan), np.zeros(n), np.full(n, np.nan)
    d1s, k2s = [], []
    a = 0.5
    for i in range(n):
        rng = hi_m[i] - lo_m[i]
        k1[i] = (macd[i] - lo_m[i]) / rng * 100 if rng > 0 else (k1[i - 1] if i else 0.0)
        d1[i] = k1[i] if (i == 0 or np.isnan(d1[i - 1])) else d1[i - 1] + a * (k1[i] - d1[i - 1])
        ld = np.nanmin(d1[max(0, i - 11):i + 1]) if i >= 11 else np.nan
        hd = np.nanmax(d1[max(0, i - 11):i + 1]) if i >= 11 else np.nan
        r2 = hd - ld
        k2[i] = (d1[i] - ld) / r2 * 100 if r2 > 0 else (k2[i - 1] if i else 0.0)
        stc[i] = k2[i] if (i == 0 or np.isnan(stc[i - 1])) else stc[i - 1] + a * (k2[i] - stc[i - 1])
    s1, s2 = sh(stc), sh(stc, 2)
    with np.errstate(invalid="ignore"):
        rise, fall = stc > s1, stc < s1
        gt = (s2 >= s1) & (stc > s1) & (stc < 25.0)
        rt = (s2 <= s1) & (stc < s1) & (stc > 75.0)
        cb, cs = cross(stc, np.full(n, 25.0), True), cross(stc, np.full(n, 75.0), False)
        if stcm == "turn":
            sb, ss = gt, rt
        elif stcm == "cross":
            sb, ss = cb, cs
        elif stcm == "slope":
            sb, ss = rise, fall
        else:
            sb, ss = gt | cb | rise, rt | cs | fall
    # MACD
    if macd_sma:
        ml = np_sma(c, 12) - np_sma(c, 26)
        ms = pd.Series(ml).rolling(9).mean().to_numpy()
    else:
        ml = np_ema(c, 12) - np_ema(c, 26)
        ms = ema_na(ml, 9)
    hist = ml - ms
    ph = sh(hist)
    with np.errstate(invalid="ignore"):
        bcr, scr = cross(ml, ms, True), cross(ml, ms, False)
        bc = (bcr & (ml <= 0)) if zero else bcr
        sc = (scr & (ml >= 0)) if zero else scr
        hu, hd_ = hist > ph, hist < ph
        if macdm == "cross":
            mb, mbr = bc, sc
        elif macdm == "slope":
            mb, mbr = hu, hd_
        elif macdm == "or":
            mb, mbr = bc | hu, sc | hd_
        else:
            mb, mbr = bc & hu, sc & hd_
    req = {"Loose": 1, "Balanced": 2, "Strict": 3}[mode]
    bcount = sb.astype(int) + mb.astype(int) + eb.astype(int)
    scount = ss.astype(int) + mbr.astype(int) + es.astype(int)
    buy = bflip & (bcount >= req)
    sell = sflip & (scount >= req)
    atr14 = np_atr(h, l, c, 14)
    lev = {}

    def orders(i, pos):
        out = []
        if np.isnan(atr14[i]):
            return out
        sld = max((150 * 0.01) if method == "rr" else atr14[i] * 1.5, 0.01 * 10)
        if method == "atr":
            ltp, stp = c[i] + atr14[i] * 3.0, c[i] - atr14[i] * 3.0
        elif method == "rr":
            ltp, stp = c[i] + 150 * 0.01 * 2.0, c[i] - 150 * 0.01 * 2.0
        else:
            ltp = stp = None
        if buy[i] and pos == 0:
            out.append(("entry", 1))
            lev[i] = (None if method == "flip" else c[i] - sld, ltp)
        if sell[i] and pos == 0:
            out.append(("entry", -1))
            lev[i] = (None if method == "flip" else c[i] + sld, stp)
        if method == "flip":
            if sflip[i] and pos > 0:
                out.append(("close", 1))
            if bflip[i] and pos < 0:
                out.append(("close", -1))
        return out

    stop = lambda i, pos, ep, eb_: lev[eb_ - 1][0] if eb_ - 1 in lev else None
    tgt = lambda i, pos, ep, eb_: lev[eb_ - 1][1] if eb_ - 1 in lev else None
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt)
    ok, d = compare(run_conversion(TV_ID, df, params=params, strategy_overrides={"slippage": 0, "commission_value": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(8000, seed=1717)
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({}, ("Balanced", "atr", "turn", "price", "or", False, False)),
             ({"Entry Mode": "Loose", "Exit Method": "Fixed RR", "STC Confirmation Mode": "Any Bullish/Bearish", "EMA Confirmation Mode": "Any EMA Bullish/Bearish",
               "MACD Confirmation Mode": "Cross And Slope"}, ("Loose", "rr", "any", "any", "and", False, False)),
             ({"Entry Mode": "Strict", "Exit Method": "FLI Flip", "STC Confirmation Mode": "Slope Only", "EMA Confirmation Mode": "EMA Slope",
               "MACD Confirmation Mode": "Slope Only", "Oscillator MA Type": "SMA", "Signal MA Type": "SMA"}, ("Strict", "flip", "slope", "slope", "slope", True, False)),
             ({"Exit Method": "Trailing", "STC Confirmation Mode": "Cross Threshold", "EMA Confirmation Mode": "Cross EMA", "MACD Confirmation Mode": "Cross Only",
               "Use MACD Zero-Line Filter": True, "Entry Mode": "Loose"}, ("Loose", "trail", "cross", "cross", "cross", False, True)))
    for params, args in cases:
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
