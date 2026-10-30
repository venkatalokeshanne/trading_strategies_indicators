"""Independent check — Quant Synthesis Strategy [JOAT] (vxQ5o39J): 15-minute bars (24 h synthetic) on a US stock chart (higher-timeframe periods counted from 09:30 New York), orders at the bar close (process_orders_on_close), commission / slippage / margin off (the quantity only needs to be positive).
Long / short confluence score = regime points (EMA spread vs ATR, ADX>=18 trend, expansion), bias points (240-minute fast EMA vs slow EMA with a positive / negative slope, lookahead off, and the last two pivots' higher highs / lows), clamped momentum points (spread, regression slope, EMA pulse, oscillator-divergence between pivots), volume points (z-score, directional volume),
and opening-range session points (09:30-16:00 NY: range of the first N bars, session open, 10-bar breakout); entry when the trend regime holds, balance does not, the score is >= minimum and above the other side, cooldown and per-session room allow (reversal allowed), exit bracket from the average entry price issued while open at script time, plus time exit, bias / regime exit, and a flat at the session's end. Uses the pending-order reference broker (simulate_ord, on_close).
Variants: defaults; 60-minute bias, minimum confluence 55, ADX length 10, 3 entries per session, cooldown 2; no HTF bias filter, session filter off, opening range 3 bars, max bars 15, stop 1.0 / target 1.5."""
import numpy as np

from indep import bars, compare, np_atr, np_dmi, np_ema, np_periods, np_security_lookahead_off, np_sma, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "vxQ5o39J"
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


def stdev0(x, n):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = x[i - n + 1:i + 1].std()
    return out


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


def piv(x, ln, high):
    out = np.full(len(x), np.nan)
    for i in range(2 * ln, len(x)):
        w = x[i - 2 * ln:i + 1]
        ctr = w[ln]
        a, b = w[:ln], w[ln + 1:]
        if (high and (a < ctr).all() and (b <= ctr).all()) or ((not high) and (a > ctr).all() and (b >= ctr).all()):
            out[i] = ctr
    return out


def clamp(v, lo, hi):
    return np.minimum(np.maximum(v, lo), hi)


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    import pandas as pd
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    insess = (mins >= 570) & (mins < 960)
    atr = np_atr(h, l, c, 14)
    atrs = np.maximum(atr, MT)
    atrp = atr / c
    sm50 = np_sma(atrp, 50)
    atravg = np.where(np.isnan(sm50), atrp, sm50)
    fe, se = ema_na(c, 12), ema_na(c, 34)
    sig = ema_na(fe - se, 9)
    esn = (fe - se) / atrs
    sn = sig / atrs
    adx = np_dmi(h, l, c, p["adx"])[2]
    with np.errstate(invalid="ignore"):
        trend = (adx >= 18) & (np.abs(esn) >= 0.20)
        balance = (adx < 16) | (atrp < atravg * 0.90)
        expansion = atrp > atravg * 1.12
    pid, last_of = np_periods(df, p["htf"])
    pcl = c[last_of]
    hf = np_security_lookahead_off(ema_na(pcl, 34), pid, last_of)
    hs = np_security_lookahead_off(ema_na(pcl, 89), pid, last_of)
    slope = hf - np.r_[np.nan, hf[:-1]]
    with np.errstate(invalid="ignore"):
        hbull = (hf > hs) & (slope > 0)
        hbear = (hf < hs) & (slope < 0)
    ph, pl = piv(h, 3, True), piv(l, 3, False)
    tsn = (linreg(c, 20, 0) - linreg(c, 20, 1)) / atrs
    pulse = ema_na(esn + tsn, 5)
    rm = np.full(n, np.nan)
    lm = np.full(n, np.nan)
    for i in range(9, n):
        rm[i] = h[i - 9:i + 1].max()
        lm[i] = l[i - 9:i + 1].min()
    hh1 = np.r_[np.nan, rm[:-1]]
    ll1 = np.r_[np.nan, lm[:-1]]
    hh1 = np.where(np.isnan(hh1), h, hh1)
    ll1 = np.where(np.isnan(ll1), l, ll1)
    vs = np_sma(v, 20)
    vsd = stdev0(v, 20)
    with np.errstate(invalid="ignore", divide="ignore"):
        vz = np.where(vsd == 0.0, 0.0, (v - vs) / vsd)
        dsc = np.maximum(np_sma(v * np.abs(c - o), 20), MT)
        dirv = (v * (c - o)) / dsc
    vscore = clamp(vz * 8.0 + dirv * 10.0, -15.0, 15.0)
    S = dict(hp=[np.nan, np.nan], lp=[np.nan, np.nan], bdp=np.nan, bdo=np.nan, udp=np.nan, udo=np.nan,
             so=np.nan, oh=np.nan, ol=np.nan, sb=0, es=0, ltb=None, eb=None, prev=0.0, pins=False)

    def orders(i, pos, info):
        out = []
        with np.errstate(invalid="ignore"):
            if not np.isnan(ph[i]):
                S["hp"] = [S["hp"][1], ph[i]]
            if not np.isnan(pl[i]):
                S["lp"] = [S["lp"][1], pl[i]]
            have = not any(np.isnan(S["hp"] + S["lp"]))
            sbull = have and S["hp"][1] > S["hp"][0] and S["lp"][1] > S["lp"][0]
            sbear = have and S["hp"][1] < S["hp"][0] and S["lp"][1] < S["lp"][0]
            bull_div = bear_div = False
            if i >= 3:
                osc = esn[i - 3] + tsn[i - 3] + sn[i - 3]
                if not np.isnan(ph[i]) and not np.isnan(osc):
                    bear_div = (not np.isnan(S["bdp"])) and ph[i] > S["bdp"] and osc < S["bdo"]
                    S["bdp"], S["bdo"] = ph[i], osc
                if not np.isnan(pl[i]) and not np.isnan(osc):
                    bull_div = (not np.isnan(S["udp"])) and pl[i] < S["udp"] and osc > S["udo"]
                    S["udp"], S["udo"] = pl[i], osc
            db = 1.0 if bull_div else (-1.0 if bear_div else 0.0)
            mom = min(max(esn[i] * 16.0 + tsn[i] * 8.0 + pulse[i] * 5.0 + db * 6.0, -25.0), 25.0) if not np.isnan(esn[i] * tsn[i] * pulse[i]) else np.nan
            ins = bool(insess[i])
            prev_ins = bool(insess[i - 1]) if i > 0 else False
            if ins and not prev_ins:
                S["so"], S["oh"], S["ol"], S["sb"], S["es"] = o[i], h[i], l[i], 1, 0
            elif ins:
                if S["sb"] < p["orb"]:
                    S["oh"], S["ol"] = max(S["oh"], h[i]), min(S["ol"], l[i])
                S["sb"] += 1
            orr = ins and S["sb"] >= p["orb"]
            orh, orl = (S["oh"], S["ol"]) if orr else (np.nan, np.nan)
            orm = (orh + orl) * 0.5 if orr else np.nan
            sl_ = (not p["sf"]) or (orr and c[i] > orh and c[i] > orm)
            ss_ = (not p["sf"]) or (orr and c[i] < orl and c[i] < orm)
            sbl = orr and c[i] > S["so"] and c[i] > orm
            sbs = orr and c[i] < S["so"] and c[i] < orm
            vsur = vz[i] > 0.8
            rl = 22 if (trend[i] and esn[i] > 0) else (14 if (expansion[i] and esn[i] > 0) else 0)
            rs = 22 if (trend[i] and esn[i] < 0) else (14 if (expansion[i] and esn[i] < 0) else 0)
            bl = (20 if hbull[i] else 0) if p["hb"] else 10
            bl += 10 if sbull else 0
            bs = (20 if hbear[i] else 0) if p["hb"] else 10
            bs += 10 if sbear else 0
            ml = min(mom, 25) if mom > 0 else 0
            ms = min(abs(mom), 25) if mom < 0 else 0
            vl = min(vscore[i], 15) if (vsur and c[i] > o[i]) else 0
            vsh = min(abs(vscore[i]), 15) if (vsur and c[i] < o[i]) else 0
            sl2 = 12 if sbl else (12 if (sl_ and c[i] > hh1[i]) else 0)
            ss2 = 12 if sbs else (12 if (ss_ and c[i] < ll1[i]) else 0)
            ls = rl + bl + ml + vl + sl2
            sh = rs + bs + ms + vsh + ss2
            lc = bool(ls >= p["mc"] and ls > sh and trend[i] and not balance[i])
            sc = bool(sh >= p["mc"] and sh > ls and trend[i] and not balance[i])
            sd = max(atr[i] * p["sa"], MT * 10)
            td = max(atr[i] * p["ta"], MT * 10)
        can = S["ltb"] is None or i - S["ltb"] >= p["cd"]
        room = S["es"] < p["me"]
        if lc and can and room and pos <= 0:
            out.append(("entry", "Long", 1, None, None))
            S["ltb"] = i
            S["es"] += 1
        if sc and can and room and pos >= 0:
            out.append(("entry", "Short", -1, None, None))
            S["ltb"] = i
            S["es"] += 1
        if pos != 0 and S["prev"] == 0:
            S["eb"] = i
        if pos == 0:
            S["eb"] = None
        if pos > 0:
            out.append(("exit", "Long Exit", "Long", info["ep"] - sd, info["ep"] + td))
        if pos < 0:
            out.append(("exit", "Short Exit", "Short", info["ep"] + sd, info["ep"] - td))
        tex = S["eb"] is not None and i - S["eb"] >= p["mb"]
        if pos > 0 and tex:
            out.append(("close", "Long"))
        if pos < 0 and tex:
            out.append(("close", "Short"))
        if pos > 0 and (sbear or hbear[i] or balance[i]):
            out.append(("close", "Long"))
        if pos < 0 and (sbull or hbull[i] or balance[i]):
            out.append(("close", "Short"))
        if (not ins) and prev_ins and pos != 0:
            out.append(("close_all",))
        S["prev"] = pos
        return out

    ref = simulate_ord(o, h, l, c, orders, on_close=True)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(adx=14, htf=240, hb=True, sf=True, orb=6, sa=1.6, ta=2.8, mb=40, cd=8, me=2, mc=70)


def check():
    df = bars(25000, seed=27, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.4
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Higher Timeframe": "60", "Min Confluence": 55, "ADX Length": 10, "Max Entries Per Session": 3, "Cooldown Bars": 2}, dict(htf=60, mc=55, adx=10, me=3, cd=2)),
             ({"Use HTF Bias Filter": False, "Require Session Context": False, "Opening Range Bars": 3, "Max Bars In Trade": 15, "Stop ATR": 1.0, "Take Profit ATR": 1.5},
              dict(hb=False, sf=False, orb=3, mb=15, sa=1.0, ta=1.5)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
