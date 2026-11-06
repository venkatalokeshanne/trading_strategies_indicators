"""Independent check — Sistema Ponderado (cQHGfHEW): daily-style bars on a stock chart (VWAP resets on the trading day), market orders at the next open, pending-order reference broker (an entry in the open direction is ignored but its exit is re-issued, replacing the old levels). Signed scores: ADX14 > 25 with DI side (+/-15), SuperTrend(3, 10) (+/-13), close vs EMA20 (+/-12), MACD(12, 26, 9) line vs signal and zero (+/-6), Ichimoku (conversion 9 / base 26 / span A,B 52 of the current bar) (+/-4) - directional; ATR14 vs 1.1 / 0.9 x its SMA20 (+/-15), VWAP side (+/-13), volume vs 1.2 / 0.8 x SMA20 (+/-12), OBV vs EMA10 (+/-6), CMF(20) beyond +/-0.05 (+/-4) - volume group. Over the last `window` bars the positive (negative) directional totals and the volume totals are summed, each divided by the window; entry when a side's total >= threshold: stop = lowest low (highest high) of 3 bars (5 after a huge-body previous bar) -/+ 2 ATR with 0 < distance <= 5 ATR, target = close +/- 2 x distance, both attached to the market entry; the opposite total >= threshold closes the position. Cooldown of 3 bars after a trade closes. The session filter (`time(...) != 0`) is always true. Commission / margin off on the pinelib side.
Variants: threshold 50, window 4; threshold 40, window 2, impulse filter off; threshold 45, window 6 with the pullback filter on."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_dmi, np_ema, np_supertrend, run_conversion, simulate_ord

TV_ID = "cQHGfHEW"


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


def sma(x, n):
    return pd.Series(x).rolling(n).mean().to_numpy()


def one(df, params, thr, wb, impulse, pull):
    import warnings
    warnings.simplefilter("ignore")
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    atr = np_atr(h, l, c, 14)
    dip, dim, adx = np_dmi(h, l, c, 14)
    _, sd = np_supertrend(h, l, c, 3.0, 10)
    e20 = np_ema(c, 20)
    macd = np_ema(c, 12) - np_ema(c, 26)
    sig = ema_na(macd, 9)
    hi = lambda k: pd.Series(h).rolling(k).max().to_numpy()
    lo = lambda k: pd.Series(l).rolling(k).min().to_numpy()
    conv, base = (hi(9) + lo(9)) / 2, (hi(26) + lo(26)) / 2
    spa, spb = (conv + base) / 2, (hi(52) + lo(52)) / 2
    atr_avg = sma(atr, 20)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    day = (ny.dt.tz_localize(None) - pd.Timedelta(minutes=570)).dt.date.to_numpy()
    hl3 = (h + l + c) / 3
    vw = np.zeros(n)
    pv = vv = 0.0
    for i in range(n):
        if i == 0 or day[i] != day[i - 1]:
            pv = vv = 0.0
        pv += hl3[i] * v[i]
        vv += v[i]
        vw[i] = pv / vv
    vavg = sma(v, 20)
    obv = np.r_[0.0, np.cumsum(np.sign(np.diff(c)) * v[1:])]
    obe = np_ema(obv, 10)
    with np.errstate(divide="ignore", invalid="ignore"):
        mfv = ((c - l) - (h - c)) / (h - l) * v
        mfv[~np.isfinite(mfv)] = np.nan
        cmf = sma(mfv, 20) / sma(v, 20)
    with np.errstate(invalid="ignore"):
        s_adx = np.where((adx > 25) & (dip > dim), 15, np.where((adx > 25) & (dim > dip), -15, 0))
        s_st = np.where(sd < 0, 13, np.where(sd > 0, -13, 0))
        s_ema = np.where(c > e20, 12, np.where(c < e20, -12, 0))
        s_macd = np.where((macd > sig) & (macd > 0), 6, np.where((macd < sig) & (macd < 0), -6, 0))
        s_ich = np.where((c > spa) & (c > spb) & (conv > base), 4, np.where((c < spa) & (c < spb) & (conv < base), -4, 0))
        s_atr = np.where(atr > atr_avg * 1.1, 15, np.where(atr < atr_avg * 0.9, -15, 0))
        s_vw = np.where(c > vw, 13, np.where(c < vw, -13, 0))
        s_vol = np.where(v > vavg * 1.2, 12, np.where(v < vavg * 0.8, -12, 0))
        s_obv = np.where(obv > obe, 6, np.where(obv < obe, -6, 0))
        s_cmf = np.where(cmf > 0.05, 4, np.where(cmf < -0.05, -4, 0))
    sdir = s_adx + s_st + s_ema + s_macd + s_ich
    svol = s_atr + s_vw + s_vol + s_obv + s_cmf
    low3, low5 = lo(3), lo(5)
    high3, high5 = hi(3), hi(5)
    log = []
    S = dict(lcb=0, pc=0)

    def orders(i, pos):
        out = []
        db = da = vb = va = 0
        for k in range(wb):
            if i - k < 0:
                continue
            pdv, pvv = sdir[i - k], svol[i - k]
            if pdv > 0:
                db += pdv
            if pdv < 0:
                da += abs(pdv)
            if pvv > 0:
                vb += pvv
            if pvv < 0:
                va += abs(pvv)
        tb, ta_ = db / wb + vb / wb, da / wb + va / wb
        if i < 1:
            return out
        apl = (not pull) or c[i - 1] > o[i - 1]
        aps = (not pull) or c[i - 1] < o[i - 1]
        imp = abs(c[i - 1] - o[i - 1]) > atr[i] * 2.0
        five = impulse and imp
        slr = (low5[i] if five else low3[i]) - atr[i] * 2.0
        ssr = (high5[i] if five else high3[i]) + atr[i] * 2.0
        sld, ssd = c[i] - slr, ssr - c[i]
        with np.errstate(invalid="ignore"):
            slv = sld > 0 and sld <= atr[i] * 5.0
            ssv = ssd > 0 and ssd <= atr[i] * 5.0
        if len(log) > S["pc"] and len(log) > 0:
            S["lcb"] = i
        S["pc"] = len(log)
        ok = (i - S["lcb"]) >= 3 or S["lcb"] == 0
        lc = tb >= thr and apl and ok
        sc = ta_ >= thr and aps and ok
        if lc and slv:
            out += [("entry", "Long", 1, None, None), ("exit", "Long Exit", "Long", slr, c[i] + sld * 2.0)]
        if sc and ssv:
            out += [("entry", "Short", -1, None, None), ("exit", "Short Exit", "Short", ssr, c[i] - ssd * 2.0)]
        if ta_ >= thr and pos > 0:
            out.append(("close", "Long"))
        if tb >= thr and pos < 0:
            out.append(("close", "Short"))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate_ord(o, h, l, c, orders, log=log)
    ok, d = compare(run_conversion(TV_ID, df, params=params, strategy_overrides={"commission_value": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(8000, seed=909)
    msgs, allok = [], True
    cases = (({"Umbral mínimo de entrada": 50}, (50, 4, True, False)),
             ({"Umbral mínimo de entrada": 40, "Velas de ventana deslizante": 2, "Filtro vela impulso gigante": False}, (40, 2, False, False)),
             ({"Umbral mínimo de entrada": 45, "Velas de ventana deslizante": 6, "Filtro anti-pullback": True}, (45, 6, True, True)))
    for params, args in cases:
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
