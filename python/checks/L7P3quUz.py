"""Independent check — VWAP Strategy Trend + Mean Reversion (L7P3quUz): 30-minute bars (24 h synthetic, compressed) on a US stock chart (trading day from 09:30 New York), market orders at the next open. A volume-weighted VWAP / standard-deviation band set restarts with the session (trading day), ISO week or month; signal = trend (VWAP / band cross) or mean reversion (outside / cross / reclaim of a band) with the volume, ATR %, band-width, VWAP-slope, ADX, deviation and RSI / EMA filters. Stops and targets are re-issued each bar while the position is open at script time (live target unless locked at entry), with the optional break-even; all stored levels are wiped on the first bar that sees the position flat (even right after a same-bar re-entry, so that exit only has its limit). Sizing does not change the trade list. Uses the pending-order reference broker (simulate_ord). Commission / margin off on the pinelib side.
Variants: trend defaults; trend with a locked target and break-even; trend with Band 1 break, RSI confluence, band-based stop and a VWAP target; mean reversion (band reclaim, ADX ceiling); mean reversion band cross on the weekly anchor with break-even and a locked target; trend EMA regime on the monthly anchor."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_dmi, np_ema, np_rsi, np_sma, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "L7P3quUz"


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None) - pd.Timedelta(minutes=570)
    if p["anchor"] == "D":
        key = ny.dt.date.to_numpy()
    elif p["anchor"] == "W":
        iso = ny.dt.isocalendar()
        key = [(int(a), int(b)) for a, b in zip(iso["year"], iso["week"])]
    else:
        key = [(int(a), int(b)) for a, b in zip(ny.dt.year, ny.dt.month)]
    tp = (h + l + c) / 3
    vw = np.zeros(n)
    sd = np.zeros(n)
    pv = vv = pv2 = 0.0
    for i in range(n):
        if i > 0 and key[i] != key[i - 1]:
            pv = vv = pv2 = 0.0
        pv += tp[i] * v[i]
        vv += v[i]
        pv2 += v[i] * tp[i] ** 2
        vw[i] = pv / vv if vv != 0 else tp[i]
        var = pv2 / vv - vw[i] ** 2 if vv != 0 else 0.0
        sd[i] = np.sqrt(max(var, 0.0))
    up = {k: vw + sd * m for k, m in ((1, p["b1"]), (2, p["b2"]), (3, p["b3"]))}
    lo = {k: vw - sd * m for k, m in ((1, p["b1"]), (2, p["b2"]), (3, p["b3"]))}
    atr = np_atr(h, l, c, 14)
    rsi = np_rsi(c, 14)
    rema = np_ema(c, 200 if p["emalen"] is None else p["emalen"])
    avgv = np_sma(v, 20)
    adx = np_dmi(h, l, c, 14)[2]

    def cu(a, b):
        pa, pb = np.r_[np.nan, a[:-1]], np.r_[np.nan, b[:-1]]
        with np.errstate(invalid="ignore"):
            return (a > b) & (pa <= pb)

    def cd(a, b):
        pa, pb = np.r_[np.nan, a[:-1]], np.r_[np.nan, b[:-1]]
        with np.errstate(invalid="ignore"):
            return (a < b) & (pa >= pb)

    lvl = lambda k: np.full(n, float(k))
    with np.errstate(invalid="ignore", divide="ignore"):
        vol_ok = v > avgv * p["vthr"]
        atrp = atr / c * 100
        vola_ok = np.ones(n, bool) if p["novola"] else atrp > 0.2
        bwp = (up[1] - lo[1]) / c * 100
        bw_ok = np.ones(n, bool) if p["nobw"] else bwp > 0.2
        slope = np.zeros(n)
        for i in range(5, n):
            slope[i] = (vw[i] - vw[i - 5]) / vw[i - 5] * 100
        sl_l = slope > 0.05
        sl_s = slope < -0.05
        base = vol_ok & vola_ok & bw_ok
        adx_ok = np.ones(n, bool) if p["noadx"] else adx < 25.0
        dist = np.where(atr > 0, (c - vw) / atr, 0.0)
        dev_ok = np.abs(dist) <= 3.0
        mr_rl, mr_rs = cu(rsi, lvl(30)), cd(rsi, lvl(70))
        if p["second"] == "RSI":
            tcl, tcs, mcl, mcs = rsi > 50, rsi < 50, mr_rl, mr_rs
        elif p["second"] == "EMA":
            tcl, tcs, mcl, mcs = c > rema, c < rema, c > rema, c < rema
        else:
            tcl = tcs = mcl = mcs = np.ones(n, bool)
        if p["tentry"] == "VWAP":
            tl, ts = cu(c, vw), cd(c, vw)
        elif p["tentry"] == "B1":
            tl, ts = cu(c, up[1]), cd(c, lo[1])
        else:
            tl, ts = cu(c, up[2]), cd(c, lo[2])
        mu, ml = up[p["mband"]], lo[p["mband"]]
        if p["mentry"] == "outside":
            ml_, ms_ = c < ml, c > mu
        elif p["mentry"] == "cross":
            ml_, ms_ = cd(c, ml), cu(c, mu)
        else:
            ml_, ms_ = (l < ml) & (c > ml), (h > mu) & (c < mu)
        if p["mode"] == "trend":
            lc = tl & base & sl_l & tcl
            sc = ts & base & sl_s & tcs
        else:
            lc = ml_ & base & adx_ok & dev_ok & mcl
            sc = ms_ & base & adx_ok & dev_ok & mcs
        if p["mode"] == "trend":
            ldist = atr * 1.5 if p["slm"] == "ATR" else np.abs(c - lo[1])
            sdist = atr * 1.5 if p["slm"] == "ATR" else np.abs(up[1] - c)
        else:
            ldist = atr * 1.5 if p["slm"] == "ATR" else np.abs(c - lo[3])
            sdist = atr * 1.5 if p["slm"] == "ATR" else np.abs(up[3] - c)
    if p["tpm"] == "vwap":
        ltgt = stgt = vw
    elif p["mode"] == "trend":
        ltgt, stgt = up[2], lo[2]
    else:
        ltgt = stgt = vw
    S = dict(ls=np.nan, ss=np.nan, lt=np.nan, st=np.nan, ea=np.nan, pp=None)
    nn = lambda x: None if np.isnan(x) else x

    def mx(a, b):
        return np.nan if np.isnan(a) or np.isnan(b) else max(a, b)

    def mn(a, b):
        return np.nan if np.isnan(a) or np.isnan(b) else min(a, b)

    def orders(i, pos, info):
        out = []
        pp, S["pp"] = S["pp"], pos
        if lc[i] and pos == 0:
            S.update(ls=c[i] - ldist[i], lt=ltgt[i], ea=atr[i])
            out.append(("entry", "Long", 1, None, None))
        if sc[i] and pos == 0:
            S.update(ss=c[i] + sdist[i], st=stgt[i], ea=atr[i])
            out.append(("entry", "Short", -1, None, None))
        ep = info.get("ep", np.nan)
        if pos > 0 and p["be"] and h[i] >= ep + S["ea"] * p["beatr"]:
            S["ls"] = mx(S["ls"], ep)
        if pos < 0 and p["be"] and l[i] <= ep - S["ea"] * p["beatr"]:
            S["ss"] = mn(S["ss"], ep)
        if pos > 0:
            out.append(("exit", "Long Exit", "Long", nn(S["ls"]), nn(S["lt"] if p["fixed"] else ltgt[i])))
        if pos < 0:
            out.append(("exit", "Short Exit", "Short", nn(S["ss"]), nn(S["st"] if p["fixed"] else stgt[i])))
        if pos == 0 and pp is not None and pp != 0:
            S.update(ls=np.nan, ss=np.nan, lt=np.nan, st=np.nan, ea=np.nan)
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate_ord(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="30", params=params, strategy_overrides={"commission_value": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(anchor="D", mode="trend", b1=1.0, b2=2.0, b3=3.0, second="None", emalen=None, tentry="VWAP", mentry="reclaim", mband=2, vthr=1.2, slm="ATR", tpm="band", fixed=False, be=False, beatr=1.0, noadx=False, novola=False, nobw=False)


def check():
    df = bars(6000, seed=29, freq="30min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Trend Entry Trigger": "Band 1 Break", "Secondary Indicator": "RSI", "Stop Loss Method": "Band Based", "Take Profit Method": "VWAP Target", "Band 1 (St Dev Mult)": 0.5},
              dict(tentry="B1", second="RSI", slm="band", tpm="vwap", b1=0.5)),
             ({"Strategy Mode": "Mean Reversion", "Volume Threshold": 0.9}, dict(mode="mr", vthr=0.9)),
             ({"Strategy Mode": "Mean Reversion", "Mean Reversion Entry Trigger": "Band Cross", "VWAP Anchor Period": "Week", "Use Break-Even Stop": True,
               "Mean Reversion Entry Band": "Band 1", "Volume Threshold": 0.8, "Band 1 (St Dev Mult)": 0.3, "Use ADX Filter": False, "Use Band Width Filter": False, "Use Volatility (ATR) Filter": False, "Profit Required Before Break-Even (ATR)": 0.5},
              dict(mode="mr", mentry="cross", anchor="W", be=True, fixed=False, mband=1, vthr=0.8, beatr=0.5, b1=0.3, noadx=True, novola=True, nobw=True)),
             ({"VWAP Anchor Period": "Month", "Secondary Indicator": "EMA Regime", "EMA Regime Length": 50, "Trend Entry Trigger": "Band 2 Break", "Band 2 (St Dev Mult)": 1.0},
              dict(anchor="M", second="EMA", emalen=50, tentry="B2", b2=1.0)),
             ({"Lock Take Profit at Entry": True, "Use Break-Even Stop": True, "Profit Required Before Break-Even (ATR)": 0.5, "Volume Threshold": 0.8},
              dict(fixed=True, be=True, beatr=0.5, vthr=0.8)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
