"""Independent check — Hybrid 3-Strategy Smart System v6.1 (ZfP0LbHE): 15-minute bars (24 h synthetic) on a US stock chart (60-minute periods counted from 09:30 New York), orders at the bar close (process_orders_on_close), commission / slippage / margin off (the risk-based quantity does not change trade prices).
Trend (EMA slope over N bars, close side, higher-timeframe close vs EMA (lookahead off), distance to EMA, ADX and slope strength) feeds three setups: a fair-value-gap pullback (gap >= ATR x min size, retest within its life, bullish / bearish confirm candle), a volume-exhaustion reversal (extreme volume + RSI + wick bar, then a close beyond its extreme within 4 bars), and a swing-break retest
(close through the last pivot, retest within 10 bars); each needs its 0-100 score >= the mode threshold and the cooldown. The first valid setup (long FVG, vol, trend, then the short ones) while flat becomes the pending signal (expires after N bars); it is entered at the close when still valid (within an ATR distance of the signal price and not too far on the wrong side of the EMA); stop and R:R target are issued with the entry.
Uses the pending-order reference broker (simulate_ord, on_close). Variants: Balanced; High Quality; only FVG + no HTF filter + session 08-17 filter; EMA 30, pivot 3, ATR 10, no volume setup."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_dmi, np_periods, np_rsi, np_security_lookahead_off, np_sma, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "ZfP0LbHE"
MT = 0.01


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


def piv(x, ln, high):
    out = np.full(len(x), np.nan)
    for i in range(2 * ln, len(x)):
        w = x[i - 2 * ln:i + 1]
        ctr = w[ln]
        a, b = w[:ln], w[ln + 1:]
        if (high and (a < ctr).all() and (b <= ctr).all()) or ((not high) and (a > ctr).all() and (b >= ctr).all()):
            out[i] = ctr
    return out


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    insess = (mins >= 480) & (mins < 1020)
    bal = p["mode"] == "Balanced"
    adx_min, vmult = (18.0, 1.4) if bal else (24.0, 1.8)
    fmin, fage, cdb, maxd, vbars = (0.20, 20, 5, 1.00, 4) if bal else (0.40, 14, 8, 0.60, 3)
    maxemad, sth, slb, slmin = (2.5, 55, 3, 0.10) if bal else (1.6, 70, 5, 0.18)
    rrf, rrv, rrt = (2.0, 2.2, 1.8) if bal else (2.2, 2.5, 2.0)
    ema = ema_na(c, p["el"])
    atr = np_atr(h, l, c, p["al"])
    rsi = np_rsi(c, 14)
    vma = np_sma(v, 20)
    adx = np_dmi(h, l, c, 14)[2]
    pid, last_of = np_periods(df, 60)
    pcl = c[last_of]
    hc = np_security_lookahead_off(pcl, pid, last_of)
    he = np_security_lookahead_off(ema_na(pcl, p["el"]), pid, last_of)
    ph, pl = piv(h, p["pv"], True), piv(l, p["pv"], False)
    S = dict(ltb=None, lsh=np.nan, lsl=np.nan, bt=np.nan, bb=np.nan, bbar=None, ba=False, st_=np.nan, sbm=np.nan, sbar=None, sa=False,
             vla=False, vsa=False, vlt=np.nan, vst=np.nan, vlb=None, vsb=None, tla=False, tsa=False, tll=np.nan, tsl=np.nan, tlb=None, tsb=None,
             pl_=False, ps=False, pe=np.nan, psl=np.nan, ptp=np.nan, pex=None)

    def orders(i, pos):
        out = []
        e = ema[i]
        a = atr[i]
        with np.errstate(invalid="ignore", divide="ignore"):
            hbull = (not p["hf"]) or hc[i] > he[i]
            hbear = (not p["hf"]) or hc[i] < he[i]
            sess = (not p["sf"]) or bool(insess[i])
            eback = ema[i - slb] if i >= slb else np.nan
            emaok = abs(c[i] - e) <= a * maxemad
            trend_ok = abs(e - eback) >= a * slmin
            trending = bool(adx[i] > adx_min and trend_ok)
            body = abs(c[i] - o[i])
            uw, lw = h[i] - max(o[i], c[i]), min(o[i], c[i]) - l[i]
            bconf, sconf = c[i] > o[i], c[i] < o[i]
            btrend = bool(c[i] > e and e > eback and hbull and sess and emaok)
            strend = bool(c[i] < e and e < eback and hbear and sess and emaok)
            hv = v[i] > vma[i] * vmult
            vr = v[i] / vma[i] if vma[i] > 0 else 0.0
            cd = S["ltb"] is None or i - S["ltb"] > cdb
            if not np.isnan(ph[i]):
                S["lsh"] = ph[i]
            if not np.isnan(pl[i]):
                S["lsl"] = pl[i]
            h2 = h[i - 2] if i >= 2 else np.nan
            l2 = l[i - 2] if i >= 2 else np.nan
            nbf, nsf = l[i] > h2, h[i] < l2
            bsz = (l[i] - h2) if nbf else 0.0
            ssz = (l2 - h[i]) if nsf else 0.0
            vnb = bool(p["fvg"] and nbf and bsz >= a * fmin and btrend and trending)
            vns = bool(p["fvg"] and nsf and ssz >= a * fmin and strend and trending)
            if vnb:
                S["bt"], S["bb"], S["bbar"], S["ba"] = l[i], h2, i, True
            if vns:
                S["st_"], S["sbm"], S["sbar"], S["sa"] = l2, h[i], i, True
            if S["ba"] and i - S["bbar"] > fage:
                S["ba"], S["bt"], S["bb"], S["bbar"] = False, np.nan, np.nan, None
            if S["sa"] and i - S["sbar"] > fage:
                S["sa"], S["st_"], S["sbm"], S["sbar"] = False, np.nan, np.nan, None
            bt_ = bool(S["ba"] and i > S["bbar"] and l[i] <= S["bt"] and h[i] >= S["bb"])
            st_t = bool(S["sa"] and i > S["sbar"] and h[i] >= S["sbm"] and l[i] <= S["st_"])
            flb = bool(p["fvg"] and btrend and cd and bt_ and bconf and c[i] > S["bb"])
            fsb = bool(p["fvg"] and strend and cd and st_t and sconf and c[i] < S["st_"])
            bfs = min(bsz / a, 2.0) * 15.0
            sfs = min(ssz / a, 2.0) * 15.0
            fls = (20 if btrend else 0) + (15 if hbull else 0) + (15 if trending else 0) + (15 if bt_ else 0) + (10 if bconf else 0) + (10 if hv else 0) + bfs
            fss = (20 if strend else 0) + (15 if hbear else 0) + (15 if trending else 0) + (15 if st_t else 0) + (10 if sconf else 0) + (10 if hv else 0) + sfs
            fl_s, fs_s = bool(flb and fls >= sth), bool(fsb and fss >= sth)
            if fl_s:
                S["ba"] = False
            if fs_s:
                S["sa"] = False
            beb = bool(p["vol"] and c[i] < e and hv and rsi[i] < 38 and c[i] > o[i] and lw > body * 0.6)
            seb = bool(p["vol"] and c[i] > e and hv and rsi[i] > 62 and c[i] < o[i] and uw > body * 0.6)
            if beb:
                S["vla"], S["vlt"], S["vlb"] = True, h[i], i
            if seb:
                S["vsa"], S["vst"], S["vsb"] = True, l[i], i
            if S["vla"] and i - S["vlb"] > 4:
                S["vla"], S["vlt"], S["vlb"] = False, np.nan, None
            if S["vsa"] and i - S["vsb"] > 4:
                S["vsa"], S["vst"], S["vsb"] = False, np.nan, None
            vlb_ = bool(p["vol"] and cd and S["vla"] and i > S["vlb"] and c[i] > S["vlt"] and bconf)
            vsb_ = bool(p["vol"] and cd and S["vsa"] and i > S["vsb"] and c[i] < S["vst"] and sconf)
            vls = (15 if c[i] > e else 0) + (20 if rsi[i] < 35 else 10) + (20 if hv else 0) + (15 if lw > body else 8) + (15 if c[i] > S["vlt"] else 0) + (10 if bconf else 0) + min(vr, 2.0) * 5.0
            vss = (15 if c[i] < e else 0) + (20 if rsi[i] > 65 else 10) + (20 if hv else 0) + (15 if uw > body else 8) + (15 if c[i] < S["vst"] else 0) + (10 if sconf else 0) + min(vr, 2.0) * 5.0
            vl_s, vs_s = bool(vlb_ and vls >= sth), bool(vsb_ and vss >= sth)
            if vl_s:
                S["vla"] = False
            if vs_s:
                S["vsa"] = False
            c1 = c[i - 1] if i else np.nan
            nbl = bool(p["tl"] and not np.isnan(S["lsh"]) and c[i] > S["lsh"] and c1 <= S["lsh"] and btrend and trending)
            nbs = bool(p["tl"] and not np.isnan(S["lsl"]) and c[i] < S["lsl"] and c1 >= S["lsl"] and strend and trending)
            if nbl:
                S["tla"], S["tll"], S["tlb"] = True, S["lsh"], i
            if nbs:
                S["tsa"], S["tsl"], S["tsb"] = True, S["lsl"], i
            if S["tla"] and i - S["tlb"] > 10:
                S["tla"], S["tll"], S["tlb"] = False, np.nan, None
            if S["tsa"] and i - S["tsb"] > 10:
                S["tsa"], S["tsl"], S["tsb"] = False, np.nan, None
            tlb_ = bool(p["tl"] and S["tla"] and cd and i > S["tlb"] and l[i] <= S["tll"] and c[i] > S["tll"] and bconf)
            tsb_ = bool(p["tl"] and S["tsa"] and cd and i > S["tsb"] and h[i] >= S["tsl"] and c[i] < S["tsl"] and sconf)
            tls = (20 if btrend else 0) + (20 if trending else 0) + (15 if hbull else 0) + (15 if l[i] <= S["tll"] else 0) + (15 if c[i] > S["tll"] else 0) + (10 if bconf else 0) + (5 if hv else 0)
            tss = (20 if strend else 0) + (20 if trending else 0) + (15 if hbear else 0) + (15 if h[i] >= S["tsl"] else 0) + (15 if c[i] < S["tsl"] else 0) + (10 if sconf else 0) + (5 if hv else 0)
            tl_s, ts_s = bool(tlb_ and tls >= sth), bool(tsb_ and tss >= sth)
            if tl_s:
                S["tla"] = False
            if ts_s:
                S["tsa"] = False
            if pos == 0 and not S["pl_"] and not S["ps"]:
                if fl_s:
                    S.update(pl_=True, ps=False, pe=c[i], psl=min(l[i], S["bb"]) - a * 0.7, pex=i + vbars)
                    S["ptp"] = S["pe"] + (S["pe"] - S["psl"]) * rrf
                elif vl_s:
                    S.update(pl_=True, ps=False, pe=c[i], psl=l[i] - a * 0.9, pex=i + vbars)
                    S["ptp"] = S["pe"] + (S["pe"] - S["psl"]) * rrv
                elif tl_s:
                    S.update(pl_=True, ps=False, pe=c[i], psl=min(l[i], S["tll"]) - a * 0.7, pex=i + vbars)
                    S["ptp"] = S["pe"] + (S["pe"] - S["psl"]) * rrt
                elif fs_s:
                    S.update(pl_=False, ps=True, pe=c[i], psl=max(h[i], S["st_"]) + a * 0.7, pex=i + vbars)
                    S["ptp"] = S["pe"] - (S["psl"] - S["pe"]) * rrf
                elif vs_s:
                    S.update(pl_=False, ps=True, pe=c[i], psl=h[i] + a * 0.9, pex=i + vbars)
                    S["ptp"] = S["pe"] - (S["psl"] - S["pe"]) * rrv
                elif ts_s:
                    S.update(pl_=False, ps=True, pe=c[i], psl=max(h[i], S["tsl"]) + a * 0.7, pex=i + vbars)
                    S["ptp"] = S["pe"] - (S["psl"] - S["pe"]) * rrt
            expired = bool((S["pl_"] or S["ps"]) and S["pex"] is not None and i > S["pex"])
            lv = bool(S["pl_"] and not expired and abs(c[i] - S["pe"]) <= a * maxd and c[i] >= e * 0.994)
            sv = bool(S["ps"] and not expired and abs(c[i] - S["pe"]) <= a * maxd and c[i] <= e * 1.006)
            valid = lv or sv
            if expired:
                S.update(pl_=False, ps=False, pe=np.nan, psl=np.nan, ptp=np.nan, pex=None)
            lr = (S["pe"] - S["psl"]) if S["pl_"] else np.nan
            sr = (S["psl"] - S["pe"]) if S["ps"] else np.nan
            lq = S["pl_"] and not np.isnan(lr) and lr > MT
            sq = S["ps"] and not np.isnan(sr) and sr > MT
            el = pos == 0 and S["pl_"] and valid
            es = pos == 0 and S["ps"] and valid
        if el and lq:
            out.append(("entry", "LONG", 1, None, None))
            out.append(("exit", "LONG EXIT", "LONG", S["psl"], S["ptp"]))
            S["ltb"] = i
            S.update(pl_=False, ps=False, pe=np.nan, psl=np.nan, ptp=np.nan, pex=None)
        if es and sq:
            out.append(("entry", "SHORT", -1, None, None))
            out.append(("exit", "SHORT EXIT", "SHORT", S["psl"], S["ptp"]))
            S["ltb"] = i
            S.update(pl_=False, ps=False, pe=np.nan, psl=np.nan, ptp=np.nan, pex=None)
        return out

    ref = simulate_ord(o, h, l, c, orders, on_close=True)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(mode="Balanced", fvg=True, vol=True, tl=True, hf=True, sf=False, el=50, al=14, pv=4)


def check():
    df = bars(30000, seed=47, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.4
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Mode": "High Quality"}, dict(mode="High Quality")),
             ({"Enable Volume Exhaustion": False, "Enable Trendline Break Retest": False, "Use Higher Timeframe Filter": False, "Use Session Filter": True},
              dict(vol=False, tl=False, hf=False, sf=True)),
             ({"EMA Length": 30, "Pivot Length": 3, "ATR Length": 10, "Enable Volume Exhaustion": False}, dict(el=30, pv=3, al=10, vol=False)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
