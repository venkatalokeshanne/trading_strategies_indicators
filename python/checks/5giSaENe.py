"""Independent check — Swordsmith Bulletproof Version 2 (5giSaENe): 5-minute bars (24 h synthetic) on a US stock chart (15-minute periods and the trading day counted from 09:30 New York), 1 contract, market orders at the next open, margin / commission / slippage off.
Opening range = high / low of the 09:30-09:45 bars of each trading day, locked after the window; breakout (close beyond the range) or retest signals before the 15:00 cutoff in the NY session on weekdays; nine-condition confluence score (15-minute EMA 9/21 trend with the close beyond the fast EMA, BOS 2 points, liquidity sweep of the previous 10-bar extreme, order block with mitigation, FVG within 50 bars,
volume flow, ATR smart trail, RSI side, session/day) >= the minimum and no prop lockout (netprofit + open P&L based daily / weekly loss, trades per day, consecutive losses, profit targets) enters at the next open; stop and TP1/TP2 distances are measured from the signal close and re-issued each bar while open (TP1 touched this bar moves the stop to break-even + offset or the smart trail); everything closed at the cutoff.
One contract only (the two TP orders each exit the whole position; the first level reached closes the trade). Uses the pending-order reference broker (simulate_ord) with the closed-trade log for the P&L mirror.
Variants: defaults (80000 bars); retest mode, ORB-mid stop, score 3, TP 1.5R / 3R, 2-tick break-even, no trail; opposite-ORB stop with OBV + divergence filters, London on, short only, tight daily loss / trade limits, score 3; fixed 3-point stop, weekly loss and daily profit target."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_periods, np_rsi, np_security_lookahead_off, np_sma, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "5giSaENe"
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


def rollx(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        out[i] = fn(w) if not np.isnan(w).all() else np.nan
    return out


def one(df, params, p, minn=8):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    hr = ny.dt.hour.to_numpy()
    dow = ((ny.dt.dayofweek + 1) % 7 + 1).to_numpy()
    dom = ny.dt.day.to_numpy()
    woy = ny.dt.isocalendar().week.to_numpy()
    inorb = (mins >= 570) & (mins < 585)
    pid1, _ = np_periods(df, 1440)
    pid, last_of = np_periods(df, 15)
    pcl = c[last_of]
    hf = np_security_lookahead_off(ema_na(pcl, 9), pid, last_of)
    hs = np_security_lookahead_off(ema_na(pcl, 21), pid, last_of)
    ph, pl = piv(h, 5, True), piv(l, 5, False)
    rsi = np_rsi(c, 14)
    rph, rpl = piv(rsi, 5, True), piv(rsi, 5, False)
    atr = np_atr(h, l, c, 14)
    vma = np_sma(v, 20)
    cp = np.r_[np.nan, c[:-1]]
    with np.errstate(invalid="ignore"):
        obv = np.cumsum(np.nan_to_num(np.sign(c - cp) * v))
    obv3 = np.r_[np.full(3, np.nan), obv[:-3]]
    hh10 = np.r_[np.nan, rollx(h, 10, np.max)[:-1]]
    ll10 = np.r_[np.nan, rollx(l, 10, np.min)[:-1]]
    dayok = np.isin(dow, [2, 3, 4, 5, 6])
    insess = ((hr >= 9) & (hr < 16) & p["ny"]) | ((hr >= 3) & (hr < 8) & p["ldn"])
    pastc = hr >= 15
    log: list = []
    S = dict(oh=np.nan, ol=np.nan, oset=False, rl=False, rs=False, lsh=np.nan, lsl=np.nan, ibear=False, ibull=False,
             bobh=np.nan, bobl=np.nan, sobh=np.nan, sobl=np.nan, boa=False, soa=False, bft=np.nan, bfb=np.nan, bfbar=None, sft=np.nan, sfb=np.nan, sfbar=None,
             trail=np.nan, tdir=0, lrh=np.nan, lph=np.nan, lrl=np.nan, lpl=np.nan, prh=np.nan, pph=np.nan, prl=np.nan, ppl=np.nan,
             lday=None, lweek=None, dsp=0.0, wsp=0.0, dtr=0, cl=0, lclosed=0, tp1=np.nan, tp2=np.nan, sp=np.nan, ep=np.nan, hit=False)

    def orders(i, pos, info):
        out = []
        with np.errstate(invalid="ignore", divide="ignore"):
            nd = i == 0 or pid1[i] != pid1[i - 1]
            if nd:
                S.update(oh=np.nan, ol=np.nan, oset=False, rl=False, rs=False)
            if inorb[i]:
                S["oh"] = h[i] if np.isnan(S["oh"]) else max(S["oh"], h[i])
                S["ol"] = l[i] if np.isnan(S["ol"]) else min(S["ol"], l[i])
            if (not inorb[i]) and not np.isnan(S["oh"]) and not S["oset"]:
                S["oset"] = True
            oh, ol = S["oh"], S["ol"]
            omid = (oh + ol) / 2 if not (np.isnan(oh) or np.isnan(ol)) else np.nan
            lbo, sbo = bool(S["oset"] and c[i] > oh), bool(S["oset"] and c[i] < ol)
            rng = (oh - ol) if not (np.isnan(oh) or np.isnan(ol)) else 0.0
            tol = rng * (0.25 / 100.0)
            if lbo:
                S["rl"] = True
            if sbo:
                S["rs"] = True
            rlg = S["rl"] and l[i] <= oh + tol and c[i] > oh
            rsh = S["rs"] and h[i] >= ol - tol and c[i] < ol
            lraw = bool(S["oset"] and (rlg if p["retest"] else lbo) and not pastc[i])
            sraw = bool(S["oset"] and (rsh if p["retest"] else sbo) and not pastc[i])
            hbull, hbear = hf[i] > hs[i] and c[i] > hf[i], hf[i] < hs[i] and c[i] < hf[i]
            c1l, c1s = hbull, hbear
            lsh, lsl = S["lsh"], S["lsl"]
            if not np.isnan(ph[i]):
                S["lsh"] = ph[i]
            if not np.isnan(pl[i]):
                S["lsl"] = pl[i]
            lsh, lsl = S["lsh"], S["lsl"]
            cm1 = c[i - 1] if i else np.nan
            bbos = (not np.isnan(lsh)) and c[i] > lsh and cm1 <= lsh
            sbos = (not np.isnan(lsl)) and c[i] < lsl and cm1 >= lsl
            bch, sch = S["ibear"] and bbos, S["ibull"] and sbos
            if bbos:
                S["ibull"], S["ibear"] = True, False
            if sbos:
                S["ibear"], S["ibull"] = True, False
            c2l, c2s = (2 if (bbos or bch) else 0), (2 if (sbos or sch) else 0)
            bsw = l[i] < ll10[i] and c[i] > ll10[i]
            ssw = h[i] > hh10[i] and c[i] < hh10[i]
            if bbos:
                for k in range(1, 6):
                    if i - k >= 0 and c[i - k] < o[i - k]:
                        S["bobh"], S["bobl"], S["boa"] = h[i - k], l[i - k], True
                        break
            if sbos:
                for k in range(1, 6):
                    if i - k >= 0 and c[i - k] > o[i - k]:
                        S["sobh"], S["sobl"], S["soa"] = h[i - k], l[i - k], True
                        break
            if S["boa"] and not np.isnan(S["bobh"]):
                if c[i] < S["bobl"] + (S["bobh"] - S["bobl"]) * 0.5:
                    S["boa"] = False
            if S["soa"] and not np.isnan(S["sobh"]):
                if c[i] > S["sobh"] - (S["sobh"] - S["sobl"]) * 0.5:
                    S["soa"] = False
            ibob = S["boa"] and not np.isnan(S["bobh"]) and l[i] <= S["bobh"] and c[i] >= S["bobl"]
            isob = S["soa"] and not np.isnan(S["sobh"]) and h[i] >= S["sobl"] and c[i] <= S["sobh"]
            h2 = h[i - 2] if i >= 2 else np.nan
            l2 = l[i - 2] if i >= 2 else np.nan
            if l[i] > h2:
                S["bft"], S["bfb"], S["bfbar"] = l[i], h2, i
            if h[i] < l2:
                S["sft"], S["sfb"], S["sfbar"] = l2, h[i], i
            bage = i - S["bfbar"] if S["bfbar"] is not None else 999
            sage = i - S["sfbar"] if S["sfbar"] is not None else 999
            ibf = (not np.isnan(S["bft"])) and bage <= 50 and c[i] >= S["bfb"] and c[i] <= S["bft"]
            isf = (not np.isnan(S["sft"])) and sage <= 50 and c[i] >= S["sfb"] and c[i] <= S["sft"]
            vab = v[i] > vma[i]
            obs = obv[i] - obv3[i]
            c6l = vab and c[i] > o[i] and ((not p["obv"]) or obs > 0)
            c6s = vab and c[i] < o[i] and ((not p["obv"]) or obs < 0)
            step = atr[i] * 2.0
            if np.isnan(S["trail"]):
                S["trail"] = c[i]
            tu, td = c[i] - step, c[i] + step
            if c[i] > S["trail"]:
                S["trail"], S["tdir"] = np.maximum(S["trail"], tu), 1
            elif c[i] < S["trail"]:
                S["trail"], S["tdir"] = np.minimum(S["trail"], td), -1
            if not np.isnan(rph[i]):
                S["prh"], S["pph"], S["lrh"], S["lph"] = S["lrh"], S["lph"], rph[i], ph[i]
            if not np.isnan(rpl[i]):
                S["prl"], S["ppl"], S["lrl"], S["lpl"] = S["lrl"], S["lpl"], rpl[i], pl[i]
            bdiv = bool(p["div"] and not np.isnan(S["pph"]) and not np.isnan(S["lph"]) and S["lph"] > S["pph"] and S["lrh"] < S["prh"])
            udiv = bool(p["div"] and not np.isnan(S["ppl"]) and not np.isnan(S["lpl"]) and S["lpl"] < S["ppl"] and S["lrl"] > S["prl"])
            c8l = bool(rsi[i] >= 50 and not bdiv)
            c8s = bool(rsi[i] <= 50 and not udiv)
            c9 = bool(insess[i] and dayok[i])
            sl_ = int(hbull) + c2l + int(bool(bsw)) + int(bool(ibob)) + int(bool(ibf)) + int(bool(c6l)) + int(S["tdir"] == 1) + int(c8l) + int(c9)
            ss_ = int(hbear) + c2s + int(bool(ssw)) + int(bool(isob)) + int(bool(isf)) + int(bool(c6s)) + int(S["tdir"] == -1) + int(c8s) + int(c9)
            closed = [t for t in log]
            net = sum((d * (xp - ep)) for d, eb, ep, xb, xp in closed)
            openp = pos * (c[i] - info["ep"]) if pos != 0 else 0.0
            isnd = S["lday"] is None or dom[i] != S["lday"]
            isnw = S["lweek"] is None or woy[i] != S["lweek"]
            if isnd:
                S["lday"] = dom[i]
            if isnw:
                S["lweek"] = woy[i]
            if isnd:
                S["dsp"], S["dtr"] = net, 0
            if isnw:
                S["wsp"] = net
            ed, ew = net - S["dsp"] + openp, net - S["wsp"] + openp
            lock = bool(ed <= -abs(p["dml"]) or ew <= -abs(p["wml"]) or S["dtr"] >= p["mtd"] or S["cl"] >= p["mcl"]
                        or (p["dpt"] > 0 and ed >= p["dpt"]) or (p["wpt"] > 0 and ew >= p["wpt"]))
            nclosed = len(closed)
            if nclosed > S["lclosed"]:
                S["dtr"] += 1
                d_, _, ep_, _, xp_ = closed[nclosed - 1]
                S["cl"] = S["cl"] + 1 if d_ * (xp_ - ep_) < 0 else 0
                S["lclosed"] = nclosed
            ltd, std = p["dir"] in ("Long Only", "Both"), p["dir"] in ("Short Only", "Both")
            cl_ = bool(ltd and sl_ >= p["ms"] and lraw and dayok[i] and insess[i] and c1l and not lock and pos == 0)
            cs_ = bool(std and ss_ >= p["ms"] and sraw and dayok[i] and insess[i] and c1s and not lock and pos == 0)

            def sd(isl):
                if p["st"] == "ATR":
                    x = atr[i] * 1.5
                elif p["st"] == "ORB Mid":
                    x = (c[i] - omid) if isl else (omid - c[i])
                elif p["st"] == "Opposite ORB":
                    x = (c[i] - ol) if isl else (oh - c[i])
                else:
                    x = p["fs"]
                x = atr[i] * 1.5 if np.isnan(x) else x
                return max(x, MT)
        for ok_, isl, nm in ((cl_, True, "Long"), (cs_, False, "Short")):
            if ok_:
                dd = sd(isl)
                sg = 1 if isl else -1
                S["ep"], S["sp"] = c[i], c[i] - sg * dd
                S["tp1"], S["tp2"] = c[i] + sg * dd * p["t1"], c[i] + sg * dd * p["t2"]
                S["hit"] = False
                out.append(("entry", nm, sg, None, None))
        if pos > 0 and h[i] >= S["tp1"] and not S["hit"]:
            S["hit"] = True
        if pos < 0 and l[i] <= S["tp1"] and not S["hit"]:
            S["hit"] = True
        if pos == 0:
            S["hit"] = False
        off = p["be"] * MT
        epn = S["ep"] if not np.isnan(S["ep"]) else c[i]
        trn = S["trail"]
        if S["hit"]:
            asl = max(epn + off, trn if not np.isnan(trn) else epn + off) if p["tat"] else epn + off
            ass = min(epn - off, trn if not np.isnan(trn) else epn - off) if p["tat"] else epn - off
        else:
            asl = S["sp"] if not np.isnan(S["sp"]) else c[i] - atr[i]
            ass = S["sp"] if not np.isnan(S["sp"]) else c[i] + atr[i]
        if pos > 0:
            out.append(("exit", "L-TP1", "Long", asl, S["tp1"]))
            out.append(("exit", "L-TP2", "Long", asl, S["tp2"]))
        if pos < 0:
            out.append(("exit", "S-TP1", "Short", ass, S["tp1"]))
            out.append(("exit", "S-TP2", "Short", ass, S["tp2"]))
        if pastc[i] and pos != 0:
            out.append(("close_all",))
        return out

    ref = simulate_ord(o, h, l, c, orders, log=log)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) >= minn, f"{d} (got {len(ref)})"


BASE = dict(ny=True, ldn=False, retest=False, obv=False, div=False, dir="Both", ms=6, st="ATR", fs=20.0, t1=1.0, t2=2.0, be=0.0, tat=True,
            dml=500.0, wml=1000.0, mtd=5, mcl=3, dpt=0.0, wpt=0.0)


def check():
    msgs, allok = [], True
    # the defaults lock out for good after 3 consecutive losses (the counter only resets on a non-losing close), so that case trades only a few times
    cases = ((80000, {}, {}, 3),
             (40000, {"Require ORB Retest": True, "Stop Type": "ORB Mid", "Min Score Required": 3, "TP1 R Multiple": 1.5, "TP2 R Multiple": 3.0, "Breakeven Offset (ticks)": 2.0,
                      "Smart Trail after TP1": False, "Max Consecutive Losses": 100},
              dict(retest=True, st="ORB Mid", ms=3, t1=1.5, t2=3.0, be=2.0, tat=False, mcl=100), 8),
             (40000, {"Stop Type": "Opposite ORB", "Use OBV Confirmation": True, "Use Divergence Filter": True, "London Session": True, "Trade Direction": "Short Only",
                      "Max Trades/Day": 2, "Daily Max Loss ($)": 15.0, "Max Consecutive Losses": 100, "Min Score Required": 3},
              dict(st="Opposite ORB", obv=True, div=True, ldn=True, dir="Short Only", mtd=2, dml=15.0, mcl=100, ms=3), 8),
             (40000, {"Stop Type": "Fixed Points", "Fixed Stop (points)": 3.0, "Weekly Max Loss ($)": 30.0, "Daily Profit Target (0=off)": 20.0, "Min Score Required": 3, "Max Consecutive Losses": 100},
              dict(st="Fixed Points", fs=3.0, wml=30.0, dpt=20.0, ms=3, mcl=100), 8))
    for nb, params, ov, minn in cases:
        df = bars(nb, seed=63, freq="5min")
        for k in ("open", "high", "low", "close"):
            df[k] = 4000 * (df[k] / 100) ** 0.15
        ok, m = one(df, params, {**BASE, **ov}, minn)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
