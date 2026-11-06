"""Independent check — SMB Fashionably Late Scalp (jDtMt9ga): 5-minute bars (24 h synthetic, compressed) on a US stock chart (trading day from 09:30 New York). Day-anchored VWAP (hlc3 x volume, reset on the trading day) vs EMA(9). Long setup: EMA below VWAP (anticipate, resting buy-stop at the price where the EMA would meet the VWAP: (vwap - (1-a) ema)/a, at least a tick above the close) or a fresh cross (react, market order); EMA up-sloping and VWAP flat-to-down over their lookbacks (percent changes), a turn (bars since the day's low >= N), the 10:00-10:45 / 10:46-13:30 New York windows, geometry (stop a third of the way from the VWAP to the day's low, target = the measured move), minimum reward:risk measured from the trigger, optional volume and flat-run vetoes, flat with the re-entry cool-down passed. The pending order is renewed or cancelled every bar; the exit is issued while the position is open at script time. Uses the pending-order reference broker (simulate_ord). Commission / margin off on the pinelib side.
Variants: defaults (anticipate); react mode with the cross-price / anchor variants; anticipate with the volume and flat-veto filters, no turn requirement and a 2.0 stop fraction (smaller RR); no session window with rr off."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, np_sma, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "jDtMt9ga"


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    tick = sym.mintick
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    day = (ny.dt.tz_localize(None) - pd.Timedelta(minutes=570)).dt.date.to_numpy()
    newday = np.array([i == 0 or day[i] != day[i - 1] for i in range(n)])
    hl3 = (h + l + c) / 3
    vw = np.full(n, np.nan)
    pv = vv = 0.0
    for i in range(n):
        if newday[i]:
            pv = vv = 0.0
        pv += hl3[i] * v[i]
        vv += v[i]
        vw[i] = pv / vv if vv > 0 else np.nan
    ema = np_ema(c, 9)
    vsma = np_sma(v, 20)
    S = dict(lod=np.nan, hod=np.nan, bsl=0, bsh=0, fr=0, lfr=0, lip=None, ps=np.nan, pt=np.nan, pp=None)
    alpha = 2.0 / 10
    nn = lambda x: None if np.isnan(x) else x

    def orders(i, pos):
        out = []
        pp, S["pp"] = S["pp"], pos
        with np.errstate(invalid="ignore", divide="ignore"):
            ec = (ema[i] - ema[i - 3]) / ema[i] * 100.0 if i >= 3 else np.nan
            vc = (vw[i] - vw[i - 10]) / vw[i] * 100.0 if i >= 10 else np.nan
            eu, ed = ec > 0.02, -ec > 0.02
            ef = not eu and not ed
            vfd = vc <= 0.05
            vfu = vc >= -0.05
            if newday[i]:
                S.update(lod=l[i], hod=h[i], bsl=0, bsh=0, fr=0, lfr=0)
            else:
                nl, nh = l[i] < S["lod"], h[i] > S["hod"]
                if nl:
                    S["lod"], S["bsl"] = l[i], 0
                else:
                    S["bsl"] += 1
                if nh:
                    S["hod"], S["bsh"] = h[i], 0
                else:
                    S["bsh"] += 1
                if nl or nh:
                    S["fr"] = S["lfr"] = 0
                elif ef:
                    S["fr"] += 1
                    S["lfr"] = max(S["lfr"], S["fr"])
                else:
                    S["fr"] = 0
            lod, hod = S["lod"], S["hod"]
            fvb = max(1, int(np.floor(p["fvmin"] / 5.0 + 0.5)))
            inw = (not p["sess"]) or (600 <= m[i] < 645) or (646 <= m[i] < 810)
            volok = (not p["volc"]) or v[i] > vsma[i]
            fvon = p["fv"] and S["lfr"] >= fvb
            pe, pw = (ema[i - 1], vw[i - 1]) if i else (np.nan, np.nan)
            cup = ema[i] > vw[i] and pe <= pw
            cdn = ema[i] < vw[i] and pe >= pw
            tl = (not p["turn"]) or S["bsl"] >= 2
            ts = (not p["turn"]) or S["bsh"] >= 2
            antic = p["antic"]
            cp = vw[i] if (p["cpm"] == "vwap" or antic) else c[i]
            ta_ = vw[i] if (p["anchor"] == "vwap" or antic) else c[i]
            sf = p["sfrac"]
            slc = ta_ - sf * (ta_ - lod)
            tlc = cp + (cp - lod)
            ssc = ta_ + sf * (hod - ta_)
            tsc = cp - (hod - cp)
            vl = lod < vw[i] and slc < c[i] and tlc > c[i]
            vs = hod > vw[i] and ssc > c[i] and tsc < c[i]
            if pos != 0 or (pos == 0 and pp is not None and pp != 0):
                S["lip"] = i
            cdok = S["lip"] is None or i - S["lip"] >= 1
            flat = pos == 0
            tr = (vw[i] - (1 - alpha) * ema[i]) / alpha
            tgl = max(tr, c[i] + tick)
            tgs = min(tr, c[i] - tick)
            erl = tgl if antic else c[i]
            ers = tgs if antic else c[i]
            rrl = (tlc - erl) / max(erl - slc, tick)
            rrs = (ers - tsc) / max(ssc - ers, tick)
            rol = p["rr"] <= 0 or rrl >= p["rr"]
            ros = p["rr"] <= 0 or rrs >= p["rr"]
            rl = (ema[i] < vw[i]) if antic else cup
            rs = (ema[i] > vw[i]) if antic else cdn
            if antic:
                gl = lod < vw[i] and tr > c[i] and slc < tgl and tlc > tgl and rol
                gs = hod > vw[i] and tr < c[i] and ssc > tgs and tsc < tgs and ros
            else:
                gl, gs = vl and rol, vs and ros
            el = bool(rl and eu and vfd and tl and inw and gl and volok and not fvon and flat and cdok)
            es = bool(rs and ed and vfu and ts and inw and gs and volok and not fvon and flat and cdok)
        if antic:
            if el:
                out.append(("entry", "Long", 1, tgl, None))
                S["ps"], S["pt"] = slc, tlc
            else:
                out.append(("cancel", "Long"))
            if es:
                out.append(("entry", "Short", -1, tgs, None))
                S["ps"], S["pt"] = ssc, tsc
            else:
                out.append(("cancel", "Short"))
        else:
            if el:
                out.append(("entry", "Long", 1, None, None))
                S["ps"], S["pt"] = slc, tlc
            if es:
                out.append(("entry", "Short", -1, None, None))
                S["ps"], S["pt"] = ssc, tsc
        if pos > 0:
            out.append(("exit", "L exit", "Long", nn(S["ps"]), nn(S["pt"])))
        if pos < 0:
            out.append(("exit", "S exit", "Short", nn(S["ps"]), nn(S["pt"])))
        return out

    ref = simulate_ord(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides={"commission_value": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(antic=True, cpm="vwap", anchor="vwap", sfrac=1.0 / 3.0, rr=1.5, sess=True, turn=True, volc=False, fv=False, fvmin=15)


def check():
    df = bars(30000, seed=515, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.15
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Entry mode": "React next bar open (market)", "Cross price for measured move": "Signal bar close", "Stop anchor mode": "Cross price -> low of day"},
              dict(antic=False, cpm="close", anchor="close")),
             ({"Require above-average volume on signal bar": True, "Veto if 9 EMA was flat too long after the turn": True, "Flat veto minutes": 20,
               "Require a prior 'turn' (distinct LOD/HOD)": False, "Minimum reward:risk to enter (0 = off)": 1.0},
              dict(volc=True, fv=True, fvmin=20, turn=False, rr=1.0)),
             ({"Restrict to ideal EST time windows": False, "Minimum reward:risk to enter (0 = off)": 0.0, "Entry mode": "React next bar open (market)"},
              dict(sess=False, rr=0.0, antic=False)))
    for params, ov in cases:
        ok, mm = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(mm)
    return allok, " | ".join(msgs)
