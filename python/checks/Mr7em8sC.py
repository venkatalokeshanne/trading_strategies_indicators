"""Independent check — Y(4.0) Strateji (Mr7em8sC): daily bars, market orders at the next open, commission / slippage / margin off. Eight scoring components (RSI, stochastic with %K/%D crosses, Bollinger zones — the source's [upper, mid, lower] unpacking of the built-in's [middle, upper, lower] is kept —, CCI, Williams %R, MFI, ADX/DI, RSI pivot divergence) give 0-3 dip / peak points; voters and the volume-boosted score trigger entries; the script keeps its own position state (percentage stop also placed as a stop order on the entry bar, ATR/score-scaled trailing stop, two-phase break-even checked on bar extremes and answered with closes at the next open, opposite-signal reversal, re-entry after an exit once a pullback of the given depth occurred, EMA-pullback entry). Uses the pending-order reference broker (simulate_ord).
Variants: defaults; fewer voters and points with the trend filter, tighter stop and trail; long only with pullback entries, re-entry and wide break-even settings; short only without the divergence component."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_cci, np_dmi, np_ema, np_rsi, np_sma, np_stoch, run_conversion, simulate_ord

TV_ID = "Mr7em8sC"


def cu(a, b):
    pa, pb = np.r_[np.nan, a[:-1]], np.r_[np.nan, b[:-1]]
    with np.errstate(invalid="ignore"):
        return (a > b) & (pa <= pb)


def cd(a, b):
    pa, pb = np.r_[np.nan, a[:-1]], np.r_[np.nan, b[:-1]]
    with np.errstate(invalid="ignore"):
        return (a < b) & (pa >= pb)


def piv(x, ln, high):
    out = np.full(len(x), False)
    for i in range(2 * ln, len(x)):
        w = x[i - 2 * ln:i + 1]
        if np.isnan(w).any():
            continue
        ctr = w[ln]
        a, b = w[:ln], w[ln + 1:]
        out[i] = ((a < ctr).all() and (b <= ctr).all()) if high else ((a > ctr).all() and (b >= ctr).all())
    return out


def rhi(x, n):
    return pd.Series(x).rolling(n).max().to_numpy()


def rlo(x, n):
    return pd.Series(x).rolling(n).min().to_numpy()


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    hl3 = (h + l + c) / 3
    rsi = np_rsi(c, 14)
    skr = np_stoch(c, h, l, 14)
    sk = np_sma(skr, 3)
    sd = np_sma(sk, 3)
    scu, scd = cu(sk, sd), cd(sk, sd)
    mid = np_sma(c, 20)
    std = pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    bbu, bbm, bbl = mid, mid + 2.0 * std, mid - 2.0 * std          # source unpacking: "upper" is the basis
    bbz_lo = bbl + (bbm - bbl) * 0.30
    bbz_up = bbu - (bbu - bbm) * 0.30
    bbdeep = (bbu - bbl) * 0.15
    cci = np_cci(c, 20)
    whi, wlo = rhi(h, 14), rlo(l, 14)
    with np.errstate(invalid="ignore", divide="ignore"):
        wr = np.where(whi != wlo, -100 * (whi - c) / (whi - wlo), -50.0)
    ch = np.r_[np.nan, np.diff(hl3)]
    up = v * np.where(ch <= 0, 0.0, hl3)
    dn = v * np.where(ch >= 0, 0.0, hl3)
    up[np.isnan(ch)] = (v * hl3)[np.isnan(ch)]
    dn[np.isnan(ch)] = (v * hl3)[np.isnan(ch)]
    su, sdn = pd.Series(up).rolling(14).sum().to_numpy(), pd.Series(dn).rolling(14).sum().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        mfi = np.where(sdn == 0, 100.0, 100.0 - 100.0 / (1.0 + su / sdn))
        mfi = np.where(np.isnan(su) | np.isnan(sdn), np.nan, mfi)
    dip_, dim_, adx = np_dmi(h, l, c, 14)
    dcu, dcd = cu(dip_, dim_), cd(dip_, dim_)
    adx3 = np.r_[np.full(3, np.nan), adx[:-3]]
    with np.errstate(invalid="ignore"):
        adx_ok = adx > adx3
    pl, ph = piv(l, p["divlb"], False), piv(h, p["divlb"], True)
    vavg = np_sma(v, 20)
    with np.errstate(invalid="ignore", divide="ignore"):
        vratio = np.where(vavg == 0, 0.0, v / vavg)
        vratio = np.where(np.isnan(vratio), 0.0, vratio)
    vmult = np.where(vratio >= 2.5, 1.25, np.where(vratio >= 1.5, 1.15, 1.0))
    ef, es, et = np_ema(c, 8), np_ema(c, 21), np_ema(c, 50)
    tbull, tbear = c > et, c < et
    tatr = np_atr(h, l, c, 14)
    tatr_avg = np_sma(tatr, 50)
    with np.errstate(invalid="ignore", divide="ignore"):
        scale = np.where(tatr_avg > 0, tatr / tatr_avg, 1.0)
    clamped = np.maximum(0.5, np.minimum(2.0, scale))
    afac = 1.0 + (clamped - 1.0) * 0.3
    S = dict(pd_=0, ep=np.nan, hs=np.nan, ls=np.nan, ts=np.nan, ta=False, sl=np.nan, led=0, bse=0, lha=np.nan, lla=np.nan, rec=0, reo=False, ppl=np.nan, prl=np.nan, bdb=-9999,
             pph=np.nan, prh=np.nan, sdb=-9999)
    nn = lambda x: None if np.isnan(x) else x

    def pts(x, thr):                     # thresholds descending (3, 2, 1)
        return 3 if x <= thr[0] else (2 if x <= thr[1] else (1 if x <= thr[2] else 0))

    def orders(i, pos):
        out = []
        with np.errstate(invalid="ignore"):
            # divergence state
            if pl[i]:
                if not np.isnan(S["ppl"]) and not np.isnan(S["prl"]):
                    if l[i - p["divlb"]] < S["ppl"] and rsi[i - p["divlb"]] > S["prl"] and rsi[i - p["divlb"]] < 50:
                        S["bdb"] = i
                S["ppl"], S["prl"] = l[i - p["divlb"]], rsi[i - p["divlb"]]
            bda = p["usediv"] and (i - S["bdb"]) <= 8
            bdf = p["usediv"] and (i - S["bdb"]) <= 3
            if ph[i]:
                if not np.isnan(S["pph"]) and not np.isnan(S["prh"]):
                    if h[i - p["divlb"]] > S["pph"] and rsi[i - p["divlb"]] < S["prh"] and rsi[i - p["divlb"]] > 50:
                        S["sdb"] = i
                S["pph"], S["prh"] = h[i - p["divlb"]], rsi[i - p["divlb"]]
            sda = p["usediv"] and (i - S["sdb"]) <= 8
            sdf = p["usediv"] and (i - S["sdb"]) <= 3
            r = rsi[i]
            dp = []
            dp.append(3 if r <= 22 else (2 if r <= 30 else (1 if r <= 38 else 0)))
            k_, d_ = sk[i], sd[i]
            if scu[i] and k_ <= 12:
                x = 3
            elif scu[i] and k_ <= 20:
                x = 2
            elif scu[i] and k_ <= 35:
                x = 1
            elif k_ <= 20 and d_ <= 20:
                x = 1
            elif k_ <= 20:
                x = 1
            else:
                x = 0
            dp.append(x)
            dp.append(3 if c[i] <= bbl[i] - bbdeep[i] else (2 if c[i] <= bbl[i] else (1 if c[i] <= bbz_lo[i] else 0)))
            dp.append(3 if cci[i] <= -200 else (2 if cci[i] <= -100 else (1 if cci[i] <= -50 else 0)))
            dp.append(3 if wr[i] <= -95 else (2 if wr[i] <= -80 else (1 if wr[i] <= -65 else 0)))
            dp.append(3 if mfi[i] <= 15 else (2 if mfi[i] <= 20 else (1 if mfi[i] <= 30 else 0)))
            dp.append(3 if (dcu[i] and adx[i] >= 25) else (2 if (dip_[i] > dim_[i] and adx_ok[i]) else (1 if dip_[i] > dim_[i] else 0)))
            dp.append(3 if bdf else (2 if bda else (1 if (p["usediv"] and (i - S["bdb"]) <= 13) else 0)))
            kp = []
            kp.append(3 if r >= 78 else (2 if r >= 70 else (1 if r >= 62 else 0)))
            if scd[i] and k_ >= 88:
                x = 3
            elif scd[i] and k_ >= 80:
                x = 2
            elif scd[i] and k_ >= 65:
                x = 1
            elif k_ >= 80 and d_ >= 80:
                x = 1
            elif k_ >= 80:
                x = 1
            else:
                x = 0
            kp.append(x)
            kp.append(3 if c[i] >= bbu[i] + bbdeep[i] else (2 if c[i] >= bbu[i] else (1 if c[i] >= bbz_up[i] else 0)))
            kp.append(3 if cci[i] >= 200 else (2 if cci[i] >= 100 else (1 if cci[i] >= 50 else 0)))
            kp.append(3 if wr[i] >= -5 else (2 if wr[i] >= -20 else (1 if wr[i] >= -35 else 0)))
            kp.append(3 if mfi[i] >= 85 else (2 if mfi[i] >= 80 else (1 if mfi[i] >= 70 else 0)))
            kp.append(3 if (dcd[i] and adx[i] >= 25) else (2 if (dim_[i] > dip_[i] and adx_ok[i]) else (1 if dim_[i] > dip_[i] else 0)))
            kp.append(3 if sdf else (2 if sda else (1 if (p["usediv"] and (i - S["sdb"]) <= 13) else 0)))
            if not p["usediv"]:
                dp[7] = kp[7] = (0 if not p["usediv"] else None)
            draw, dvt = sum(dp), sum(1 for x in dp if x >= 1)
            praw, pvt = sum(kp), sum(1 for x in kp if x >= 1)
            dsc, psc = draw * vmult[i], praw * vmult[i]
            afc = afac[i]
            bta, btp = p["tact"] * afc, p["tpct"] * afc
            rdip = dvt >= p["minv"] and dsc >= p["mint"]
            rpeak = pvt >= p["minv"] and psc >= p["mint"]
            if p["trend"] and rdip and tbear[i]:
                rdip = False
            if p["trend"] and rpeak and tbull[i]:
                rpeak = False
            pd_ = S["pd_"]
            if pd_ == 0 and S["reo"]:
                S["bse"] += 1
            if pd_ == 0 and S["reo"] and S["bse"] > 80:
                S.update(reo=False, lha=np.nan, lla=np.nan)
            if pd_ == 0 and S["reo"]:
                S["lha"] = h[i] if np.isnan(S["lha"]) else max(S["lha"], h[i])
                S["lla"] = l[i] if np.isnan(S["lla"]) else min(S["lla"], l[i])
            rdl = rds = rtl = rts = False
            if pd_ == 0 and p["usere"] and S["reo"] and S["bse"] >= 5 and S["rec"] < 3:
                if S["led"] == 1 and not np.isnan(S["lha"]) and S["lha"] > 0:
                    rdl = (S["lha"] - l[i]) / S["lha"] * 100 >= p["repb"]
                    rtl = c[i] > ef[i] and c[i] > es[i]
                if S["led"] == -1 and not np.isnan(S["lla"]) and S["lla"] > 0:
                    rds = (h[i] - S["lla"]) / S["lla"] * 100 >= p["repb"]
                    rts = c[i] < ef[i] and c[i] < es[i]
            rel = rdl and rtl and dvt >= 3
            res = rds and rts and pvt >= 3
            pbl = psh = False
            bl = all(c[i - k] > o[i - k] for k in range(p["pbbar"])) if i >= 6 else False
            bs = all(c[i - k] < o[i - k] for k in range(p["pbbar"])) if i >= 6 else False
            touched = False
            for k in range(p["pbbar"] + 3):
                if i - k >= 0 and es[i] > 0:
                    if abs(l[i - k] - es[i]) / es[i] * 100 <= p["pbd"] * 1.5:
                        touched = True
                    if abs(h[i - k] - es[i]) / es[i] * 100 <= p["pbd"] * 1.5:
                        touched = True
            strong = adx[i] >= 25
            pbls = p["usepb"] and pd_ != 1 and tbull[i] and dip_[i] > dim_[i] and strong and dvt >= 2 and touched and bl and c[i] > es[i]
            pbss = p["usepb"] and pd_ != -1 and tbear[i] and dim_[i] > dip_[i] and strong and pvt >= 2 and touched and bs and c[i] < es[i]
            ndip = rdip and pd_ != 1
            npeak = rpeak and pd_ != -1
            gl = (ndip or rel or pbls) and p["dir"] != "Sadece Short"
            gs = (npeak or res or pbss) and p["dir"] != "Sadece Long"
            ccl, ccs = gs and pd_ == 1, gl and pd_ == -1
            if p["dir"] == "Sadece Long" and rpeak and pd_ == 1:
                gs = False
            if p["dir"] == "Sadece Short" and rdip and pd_ == -1:
                gl = False
            irl = rel and gl and not ndip
            irs = res and gs and not npeak
            ipl = pbls and gl and not ndip and not rel
            ips = pbss and gs and not npeak and not res
            cn = on = 0.0
            if pd_ == 1:
                cn, on = praw / 24, draw / 24
            elif pd_ == -1:
                cn, on = draw / 24, praw / 24
            sf = max(0.15, min(1.5, 1.0 - cn * 0.5 + on * 0.2))
            etp = btp * sf
            thl = p["trail"] and pd_ == 1 and S["ta"] and not np.isnan(S["ts"]) and l[i] <= S["ts"]
            ths = p["trail"] and pd_ == -1 and S["ta"] and not np.isnan(S["ts"]) and h[i] >= S["ts"]
            shl = p["sl"] and pd_ == 1 and not np.isnan(S["sl"]) and l[i] <= S["sl"]
            shs = p["sl"] and pd_ == -1 and not np.isnan(S["sl"]) and h[i] >= S["sl"]
            sxl, sxs = shl and not gs, shs and not gl
            txl, txs = thl and not gs and not sxl, ths and not gl and not sxs
            cls_l, cls_s = ccl or txl or sxl, ccs or txs or sxs
            if gl:
                S.update(pd_=1, ep=c[i], hs=c[i], ls=c[i], ts=np.nan, ta=False)
                use = p["slp"] * 0.65 if ipl else p["slp"]
                S["sl"] = c[i] - c[i] * use / 100 if p["sl"] else np.nan
                S["rec"] = S["rec"] + 1 if irl else 0
                S.update(reo=False, bse=0, lha=np.nan, lla=np.nan)
            elif gs:
                S.update(pd_=-1, ep=c[i], hs=c[i], ls=c[i], ts=np.nan, ta=False)
                use = p["slp"] * 0.65 if ips else p["slp"]
                S["sl"] = c[i] + c[i] * use / 100 if p["sl"] else np.nan
                S["rec"] = S["rec"] + 1 if irs else 0
                S.update(reo=False, bse=0, lha=np.nan, lla=np.nan)
            elif cls_l or cls_s:
                if S["pd_"] == 1:
                    S["led"] = 1
                elif S["pd_"] == -1:
                    S["led"] = -1
                S.update(reo=True, bse=0, lha=np.nan, lla=np.nan, pd_=0, ts=np.nan, ta=False, sl=np.nan)
            else:
                if S["pd_"] == 1:
                    S["hs"] = max(S["hs"], h[i])
                    if p["trail"] and not np.isnan(S["ep"]) and S["ep"] > 0:
                        if (S["hs"] - S["ep"]) / S["ep"] * 100 >= bta:
                            S["ta"], S["ts"] = True, S["hs"] * (1 - etp / 100)
                    if p["be"] and p["sl"] and not np.isnan(S["ep"]) and S["ep"] > 0:
                        cp = (c[i] - S["ep"]) / S["ep"] * 100
                        if cp >= p["be3"]:
                            p3 = S["ep"] * (1 + p["be3l"] / 100)
                            if np.isnan(S["sl"]) or p3 > S["sl"]:
                                S["sl"] = p3
                        elif cp >= p["be2"]:
                            if np.isnan(S["sl"]) or S["ep"] > S["sl"]:
                                S["sl"] = S["ep"]
                elif S["pd_"] == -1:
                    S["ls"] = min(S["ls"], l[i])
                    if p["trail"] and not np.isnan(S["ep"]) and S["ep"] > 0:
                        if (S["ep"] - S["ls"]) / S["ep"] * 100 >= bta:
                            S["ta"], S["ts"] = True, S["ls"] * (1 + etp / 100)
                    if p["be"] and p["sl"] and not np.isnan(S["ep"]) and S["ep"] > 0:
                        cp = (S["ep"] - c[i]) / S["ep"] * 100
                        if cp >= p["be3"]:
                            p3 = S["ep"] * (1 - p["be3l"] / 100)
                            if np.isnan(S["sl"]) or p3 < S["sl"]:
                                S["sl"] = p3
                        elif cp >= p["be2"]:
                            if np.isnan(S["sl"]) or S["ep"] < S["sl"]:
                                S["sl"] = S["ep"]
            lid = "RE Long" if irl else ("PB Long" if ipl else "LONG")
            sid = "RE Short" if irs else ("PB Short" if ips else "SHORT")
            if gl:
                if pos < 0:
                    out += [("close", "SHORT"), ("close", "RE Short"), ("close", "PB Short")]
                out.append(("entry", lid, 1, None, None))
                if p["sl"] and not np.isnan(S["sl"]):
                    out.append(("exit", "SL_" + lid, lid, S["sl"], None))
            elif gs:
                if pos > 0:
                    out += [("close", "LONG"), ("close", "RE Long"), ("close", "PB Long")]
                out.append(("entry", sid, -1, None, None))
                if p["sl"] and not np.isnan(S["sl"]):
                    out.append(("exit", "SL_" + sid, sid, S["sl"], None))
            if sxl or txl:
                out += [("close", "LONG"), ("close", "RE Long"), ("close", "PB Long")]
            if sxs or txs:
                out += [("close", "SHORT"), ("close", "RE Short"), ("close", "PB Short")]
            if p["dir"] == "Sadece Long" and rpeak and pd_ == 1 and not gs:
                out += [("close", "LONG"), ("close", "RE Long"), ("close", "PB Long")]
            if p["dir"] == "Sadece Short" and rdip and pd_ == -1 and not gl:
                out += [("close", "SHORT"), ("close", "RE Short"), ("close", "PB Short")]
        return out

    ref = simulate_ord(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(minv=5, mint=10, dir="Her Ikisi", usediv=True, divlb=5, trend=False, sl=True, slp=2.0, trail=True, tact=1.5, tpct=0.7, be=True, be2=0.5, be3=1.0, be3l=0.3,
            usere=True, repb=0.5, usepb=False, pbbar=2, pbd=0.3)


def check():
    df = bars(5000, seed=1717)
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.7
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Min Aktif Bilesen (N/8)": 3, "Min Toplam Puan": 5, "Trend Filtresi Aktif": True, "Stop Loss (%)": 1.5, "Temel Aktivasyon Kar (%)": 1.0},
              dict(minv=3, mint=5, trend=True, slp=1.5, tact=1.0)),
             ({"Min Aktif Bilesen (N/8)": 3, "Min Toplam Puan": 5, "Islem Yonu": "Sadece Long", "Pullback Girisi Aktif": True, "Min Pullback Derinligi (%)": 0.3,
               "Faz 2: BE Aktivasyon (%)": 1.5, "Faz 3: Garanti Aktivasyon (%)": 3.0},
              dict(minv=3, mint=5, dir="Sadece Long", usepb=True, repb=0.3, be2=1.5, be3=3.0)),
             ({"Min Aktif Bilesen (N/8)": 4, "Min Toplam Puan": 7, "Islem Yonu": "Sadece Short", "Diverjans Aktif": False, "Trailing Stop Aktif": False},
              dict(minv=4, mint=7, dir="Sadece Short", usediv=False, trail=False)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
