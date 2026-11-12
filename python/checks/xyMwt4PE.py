"""Independent check — TQQQ AG v16 Vol Overlay (xyMwt4PE): 7000 daily business-day bars of a synthetic leveraged ETF (TQQQ-like, ~3x the regime series' moves) on a stock-style symbol, with a QQQ-like regime series served through the data provider; orders at the bar's close (process_orders_on_close), the script's own equity-based quantities (equity mirrored from closed trades + open P&L), commission / slippage off.
The QQQ regime (200 SMA with buffers, 50 SMA fast triggers, RSI(10) of both series), the five-state machine (bull long, overbought short with fixed / trailing stop, bear-bounce long, bear short with trailing stop and cooldown), the optional weekly-MACD gate (QQQ weekly, lookahead off), the equity kill-switch / re-arm, the volatility overlay (fast / slow annualised vol, rising-vol penalty, instant cuts, slow restores), graded de-levering and the strategy.order rescale with a dead-band are restated bar by bar.
Uses the quantity-aware bracket reference (indep.simulate_brackets with its strategy.order netting action). Variants: defaults; kill-switch 15 % with a lower target volatility and a tighter dead-band; weekly MACD gate on, no fast bear / bull, graded de-levering with the kill-switch off; overlay off with longs disabled."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_ema, np_rsi, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "xyMwt4PE"
BASE = dict(sma_bull=0.35, sma_bear=0.75, ob=81, reentry=71, rearm=78, retrig=73, rsfilt=69, bear_os=31, bexit=55, maxb=4, obstop=7.0, obtrail=1.5,
            rs_arm=53, rs_trig=55, macd=False, fbear=True, fbull=True, longs=True, shorts=True, lev=(1.25, 1.5, 1.5, 3.0), bstrail=15.0, bscd=5, kill=65.0,
            ovl=True, tgt=0.55, fast=10, slow=60, floor=0.30, gamma=0.60, restore=0.02, band=0.03, grd=False, gx=40.0, gy=75.0, gfl=0.25)


def rolling_std(x, n):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = np.std(x[i - n + 1:i + 1])
    return out


def one(df, qq, params, p):
    p = {**BASE, **p}
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    qc = qq["close"].to_numpy()
    n = len(c)
    rsi_t, rsi_q = np_rsi(c, 10), np_rsi(qc, 10)
    sma200, sma50 = np_sma(qc, 200), np_sma(qc, 50)
    gate_a = c > np_ema(c, 18)
    gate_b = np_ema(c, 3) > np_ema(c, 22)
    # weekly MACD of the regime series (Monday-start weeks, lookahead off: a week's value shows from its last bar on)
    wk = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None).dt.to_period("W-SUN").astype(str).to_numpy()
    last_of = np.r_[wk[1:] != wk[:-1], True]
    wc = qc[last_of]
    macd_w = np_ema(wc, 12) - np_ema(wc, 26)
    sig_w = np_ema(macd_w, 9)
    pid = np.cumsum(np.r_[True, wk[1:] != wk[:-1]]) - 1
    mw = np.array([macd_w[pid[i]] if last_of[i] else (macd_w[pid[i] - 1] if pid[i] > 0 else np.nan) for i in range(n)])
    sw = np.array([sig_w[pid[i]] if last_of[i] else (sig_w[pid[i] - 1] if pid[i] > 0 else np.nan) for i in range(n)])
    ret1 = np.r_[0.0, c[1:] / c[:-1] - 1.0]
    vf, vs = rolling_std(ret1, p["fast"]) * np.sqrt(252), rolling_std(ret1, p["slow"]) * np.sqrt(252)
    log: list = []
    S = dict(in_bull=False, prev_bull=False, state=0, bb=0, bsb=0, rp=False, orp=False, obl=np.nan, bsl=np.nan, bscd=0, halted=False, hsb=False, rpk=np.nan, mprev=1.0, epk=np.nan, below=False, above=False)

    def equity(info, i):
        real = sum(d * (xp - ep) * q for d, _, ep, _, xp, q in log)
        openp = sum(x["d"] * x["q"] * (c[i] - x["ep"]) for x in info["lots"])
        return 10000.0 + real + openp

    def orders(i, info):
        out = []
        pos, avg = info["pos"], info["avg"]
        prev_bull = S["in_bull"]
        with np.errstate(invalid="ignore"):
            bt, br = sma200[i] * (1 + p["sma_bull"] / 100), sma200[i] * (1 - p["sma_bear"] / 100)
            if qc[i] > bt:
                S["in_bull"] = True
            elif qc[i] < br:
                S["in_bull"] = False
            ib = S["in_bull"]
            just = (not ib) and prev_bull
            below = bool(qc[i] < sma50[i] * (1 - 1.0 / 100))
            above = bool(qc[i] > sma50[i])
            fbt = p["fbear"] and (not ib) and below and not S["below"] and rsi_q[i] < 45
            fbc = p["fbull"] and (not ib) and above and not S["above"] and rsi_t[i] > 50
        S["below"], S["above"] = below, above
        st = S["state"]
        S["obl"] = c[i] if (st == 2 and np.isnan(S["obl"])) else min(S["obl"], c[i]) if st == 2 else np.nan
        sep = avg if pos < 0 else np.nan
        with np.errstate(invalid="ignore"):
            hit_stop = (not np.isnan(sep)) and st == 2 and c[i] >= sep * (1 + p["obstop"] / 100)
            hit_trail = (not np.isnan(S["obl"])) and st == 2 and c[i] >= S["obl"] * (1 + p["obtrail"] / 100)
        obx = hit_stop or hit_trail
        S["bsl"] = (c[i] if np.isnan(S["bsl"]) else min(S["bsl"], c[i])) if st == 5 else np.nan
        with np.errstate(invalid="ignore"):
            bsx = p["bstrail"] > 0 and (not np.isnan(S["bsl"])) and st == 5 and c[i] >= S["bsl"] * (1 + p["bstrail"] / 100)
        qr, tr = rsi_q[i], rsi_t[i]
        tg = bool(gate_a[i] and gate_b[i])
        if ib:
            S["bsb"], S["rp"] = 0, False
            if qr >= p["ob"]:
                st, S["orp"] = 2, False
            elif st == 2 and (tr < p["reentry"] or obx):
                st = 1 if tg else 0
            elif S["orp"] and qr <= p["retrig"] and tr < p["rsfilt"]:
                st, S["orp"] = 2, False
            elif st != 1 and st != 2:
                st = 1 if tg else 0
            if st == 1 and qr >= p["rearm"]:
                S["orp"] = True
            if st != 1:
                S["orp"] = False
        else:
            S["orp"] = False
            if just or fbt:
                st, S["bsb"], S["rp"] = 5, 0, False
            elif fbc:
                st, S["bsb"] = 1, 0
            elif st == 1:
                S["bsb"] = 0
            elif st == 5:
                S["bsb"] += 1
                if tr <= p["bear_os"]:
                    st, S["bb"], S["bsb"] = 3, 0, 0
                elif bsx:
                    st, S["bsb"], S["bscd"] = 0, 0, p["bscd"]
            elif tr <= p["bear_os"]:
                if st != 3:
                    st, S["bb"] = 3, 0
            elif st == 3:
                S["bb"] += 1
                if tr >= p["bexit"] or S["bb"] >= p["maxb"]:
                    st, S["bb"] = 0, 0
            else:
                st, S["bb"] = 0, 0
            if st == 0:
                if S["bscd"] > 0:
                    S["bscd"] -= 1
                if qr >= p["rs_arm"]:
                    S["rp"] = True
                with np.errstate(invalid="ignore"):
                    mb = bool(mw[i] < sw[i])
                if S["rp"] and qr <= p["rs_trig"] and ((not p["macd"]) or mb) and S["bscd"] == 0:
                    st, S["rp"], S["bsb"] = 5, False, 0
        S["state"] = st
        eq = equity(info, i)
        S["rpk"] = eq if np.isnan(S["rpk"]) else S["rpk"]
        if p["kill"] > 0:
            if (not S["halted"]) and eq <= S["rpk"] * (1 - p["kill"] / 100.0):
                S["halted"], S["hsb"] = True, not ib
            elif S["halted"]:
                if not ib:
                    S["hsb"] = True
                if S["hsb"] and ib:
                    S["halted"], S["rpk"] = False, eq
        if not S["halted"]:
            S["rpk"] = max(S["rpk"], eq)
        v_fast, v_slow = vf[i], vs[i]
        v_est = max(v_fast, v_slow) if not (np.isnan(v_fast) or np.isnan(v_slow)) else np.nan
        pen = min(0.60, max(0.0, p["gamma"] * (v_fast / max(v_slow, 1e-6) - 1.0))) if not np.isnan(v_slow) else np.nan
        if np.isnan(v_slow) or v_slow <= 0:
            m_raw = 1.0
        else:
            m_raw = max(p["floor"] * 0.5, min(1.0, max(p["floor"], p["tgt"] / max(v_est, 1e-6)) * (1.0 - pen)))
        m_now = m_raw if m_raw < S["mprev"] else min(m_raw, S["mprev"] + p["restore"])
        S["mprev"] = m_now
        S["epk"] = eq if np.isnan(S["epk"]) else max(S["epk"], eq)
        own = (1.0 - eq / S["epk"]) * 100.0 if S["epk"] > 0 else 0.0
        grd = 1.0 if not p["grd"] else 1.0 if own <= p["gx"] else p["gfl"] if own >= p["gy"] else 1.0 - (1.0 - p["gfl"]) * (own - p["gx"]) / max(p["gy"] - p["gx"], 1e-6)
        om = (m_now if p["ovl"] else 1.0) * grd
        wl = (st == 1 or st == 3) and p["longs"] and not S["halted"]
        ws = (st == 2 or st == 5) and p["shorts"] and not S["halted"]
        lev_l = p["lev"][1] if st == 3 else p["lev"][0]
        lev_s = p["lev"][3] if st == 2 else p["lev"][2]
        ql = max(1, np.floor(eq * lev_l * om / c[i]))
        qs = max(1, np.floor(eq * lev_s * om / c[i]))
        if wl and pos <= 0:
            out.append(("entry", "Long", 1, float(ql)))
        if ws and pos >= 0:
            out.append(("entry", "Short", -1, float(qs)))
        if (not wl) and (not ws) and pos != 0:
            out.append(("close_all",))
        pd_ = 1 if pos > 0 else -1 if pos < 0 else 0
        wd = 1 if wl else -1 if ws else 0
        if p["ovl"] and pd_ != 0 and pd_ == wd:
            lev = lev_l if pd_ > 0 else lev_s
            tq = max(1, np.floor(eq * lev * om / c[i])) * pd_
            dev = abs(tq - pos) / max(abs(pos), 1)
            if dev > p["band"]:
                dq = tq - pos
                if dq > 0:
                    out.append(("order", "RescaleUp", 1, float(dq)))
                elif dq < 0:
                    out.append(("order", "RescaleDn", -1, float(-dq)))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, on_close=True, tick=0.01, qty_step=1e-9, log=log)
    sym = SymbolInfo.make("NASDAQ:TQQQ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params, data_provider=lambda s, tf: qq,
                                     strategy_overrides={"commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


def check():
    q = bars(7000, seed=1301, freq="B")
    lc = np.log(q["close"].to_numpy() / 100)
    trend = np.polyval(np.polyfit(np.arange(len(lc)), lc, 1), np.arange(len(lc)))
    det = lc - trend                                    # drift-free log level so prices stay in a normal range for the whole run
    t = q.copy()
    for k in ("open", "high", "low", "close"):
        rel = q[k].to_numpy() / q["close"].to_numpy()
        q[k] = 100 * np.exp(0.6 * det) * rel
        t[k] = 60 * np.exp(1.8 * det) * rel
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Equity Kill-Switch DD % (0=off)": 15.0, "Target Volatility  (0.55 / 0.75 / 0.90)": 0.35, "Rebalance Deadband": 0.01}, dict(kill=15.0, tgt=0.35, band=0.01)),
             ({"Use Weekly MACD Gate": True, "Use Fast Bear (50 SMA)": False, "Use Fast Bull (50 SMA)": False, "Enable Graded De-levering": True, "Equity Kill-Switch DD % (0=off)": 0.0},
              dict(macd=True, fbear=False, fbull=False, grd=True, kill=0.0)),
             ({"Enable Volatility Overlay": False, "Enable Longs": False}, dict(ovl=False, longs=False)))
    for params, ov in cases:
        ok, m = one(t, q, params, ov)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
