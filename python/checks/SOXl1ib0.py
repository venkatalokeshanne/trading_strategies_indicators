"""Independent check — Master Structural Engine (SOXl1ib0): 15-minute bars, market orders at the next open, one position (reversal by an opposing signal), session 09:00-22:00 UTC+3. Setup (long): EMA5(high) > EMA100(high); Heikin-Ashi doji filter (HA body >= 40 % of the HA range); momentum (RSI14 >= 55, or >= 50 after a close above the previous high or any of the last 6 bars touching the EMA100 low; close and HA close above both EMA5 and EMA100 high); clean-HA-wick (HA low >= HA open unless engulfing); a pullback within the last 6 bars (low <= EMA100 high) with close and HA close above the EMA200 on every bar since; compression (|EMA100 high - EMA200| >= 30 ticks); news spike (range two bars ago <= 2.5 ATR then). Entry once (blocked until the low touches the EMA100 high or the close falls under the EMA200); stop = EMA100 low - 10 ticks, target = 3R; levels live in script state and the exit is re-issued every bar with the latest values (also after an ignored same-direction entry); everything is closed outside the session. Short mirrored. Margin off on the pinelib side. Variants: all filters on; momentum, wick, compression and news off with a 2R target; doji, wick and override off."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "SOXl1ib0"


def one(df, params, f):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    mt, rr = 0.01, params.get("Reward/Risk Ratio", 3.0)
    hc = (o + h + l + c) / 4
    ho = np.zeros(n)
    ho[0] = (o[0] + c[0]) / 2
    for i in range(1, n):
        ho[i] = (ho[i - 1] + hc[i - 1]) / 2
    hh, hl = np.maximum(h, np.maximum(ho, hc)), np.minimum(l, np.minimum(ho, hc))
    e5h, e5l = np_ema(h, 5), np_ema(l, 5)
    e1h, e1l = np_ema(h, 100), np_ema(l, 100)
    e2 = np_ema(c, 200)
    rsi, atr = np_rsi(c, 14), np_atr(h, l, c, 14)
    loc = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert(pd.Timestamp(0, tz="UTC").tz).dt.tz_localize(None) + pd.Timedelta(hours=3)
    m = (loc.dt.hour * 60 + loc.dt.minute).to_numpy()
    ins = (m >= 540) & (m < 1320)
    S = dict(bl=False, bs=False, sl=np.nan, tp=np.nan)
    AL, AS = {}, {}

    def orders(i, pos):
        out = []
        if i < 220:
            return out
        engl, engs = c[i] > h[i - 1], c[i] < l[i - 1]
        dl = any(l[i - k] <= e1l[i - k] for k in range(1, 7))
        ds = any(h[i - k] >= e1h[i - k] for k in range(1, 7))
        dj = True
        if f["doji"]:
            rg = hh[i] - hl[i]
            if rg == 0 or abs(hc[i] - ho[i]) / rg * 100 < 40:
                dj = False
        news = not (f["news"] and (h[i - 2] - l[i - 2]) > atr[i - 2] * 2.5)
        ml = ms = True
        if f["mom"]:
            tl = 50.0 if (f["ovr"] and (engl or dl)) else 55.0
            if rsi[i] < tl or rsi[i] < 50 or c[i] <= e5h[i] or c[i] <= e1h[i] or hc[i] <= e5h[i] or hc[i] <= e1h[i]:
                ml = False
            ts = 50.0 if (f["ovr"] and (engs or ds)) else 45.0
            if rsi[i] > ts or rsi[i] > 50 or c[i] >= e5l[i] or c[i] >= e1l[i] or hc[i] >= e5l[i] or hc[i] >= e1l[i]:
                ms = False
        wl = not (f["wick"] and not (f["ovr"] and engl) and hl[i] < ho[i])
        ws = not (f["wick"] and not (f["ovr"] and engs) and hh[i] > ho[i])
        vl = any(l[i - k] <= e1h[i - k] and all(not (c[i - q] <= e2[i - q] or hc[i - q] <= e2[i - q]) for q in range(k + 1)) for k in range(1, 7))
        vs = any(h[i - k] >= e1l[i - k] and all(not (c[i - q] >= e2[i - q] or hc[i - q] >= e2[i - q]) for q in range(k + 1)) for k in range(1, 7))
        cl = not (f["comp"] and abs(e1h[i] - e2[i]) < 30 * mt)
        cs = not (f["comp"] and abs(e1l[i] - e2[i]) < 30 * mt)
        setl = e5h[i] > e1h[i] and news and dj and ml and wl and vl and cl
        sets = e5l[i] < e1l[i] and news and dj and ms and ws and vs and cs
        buy = setl and c[i] > e2[i] and hc[i] > e2[i]
        sell = sets and c[i] < e2[i] and hc[i] < e2[i]
        if l[i] <= e1h[i] or c[i] < e2[i]:
            S["bl"] = False
        if h[i] >= e1l[i] or c[i] > e2[i]:
            S["bs"] = False
        el = buy and not S["bl"] and ins[i]
        es = sell and not S["bs"] and ins[i]
        if el:
            if pos < 0:
                out.append(("close", -1))
            S["sl"] = e1l[i] - 10 * mt
            S["tp"] = c[i] + (c[i] - S["sl"]) * rr
            out.append(("entry", 1))
            S["bl"] = True
        if es:
            if pos > 0:
                out.append(("close", 1))
            S["sl"] = e1h[i] + 10 * mt
            S["tp"] = c[i] - (S["sl"] - c[i]) * rr
            out.append(("entry", -1))
            S["bs"] = True
        if pos > 0 or el:
            AL[i] = (S["sl"], S["tp"])
        if pos < 0 or es:
            AS[i] = (S["sl"], S["tp"])
        if pos == 0 and not el and not es:
            S["sl"] = S["tp"] = np.nan
        if not ins[i]:
            if pos != 0:
                out.append(("close", pos))
            S["bl"] = S["bs"] = False
            S["sl"] = S["tp"] = np.nan
        return out

    def lvl(i, pos, k):
        a = (AL if pos > 0 else AS).get(i - 1)
        if a is None or np.isnan(a[k]):
            return None
        return a[k]

    stop = lambda i, pos, ep, eb: lvl(i, pos, 0)
    tgt = lambda i, pos, ep, eb: lvl(i, pos, 1)
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt)
    sym = SymbolInfo.make("OANDA:EURUSD", "forex", mintick=0.01, qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(30000, seed=311, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.35
    msgs, allok = [], True
    on = dict(doji=True, news=True, mom=True, wick=True, comp=True, ovr=True)
    off = dict(doji=True, news=False, mom=False, wick=False, comp=False, ovr=True)
    mid = dict(doji=False, news=True, mom=True, wick=False, comp=True, ovr=False)
    cases = (({}, on),
             ({"Filter 1: Strict Momentum (RSI > 55 / < 45)": False, "Filter 2: Clean Heikin Ashi Wick Filter": False,
               "Filter 3: Dynamic Compression Gap": False, "Filter 5: News Spike/ATR Protection": False, "Reward/Risk Ratio": 2.0}, off),
             ({"Filter 4: Indecision Doji Filter (Absolute)": False, "Filter 2: Clean Heikin Ashi Wick Filter": False,
               "Smart Override: Deep Pullbacks & Engulfing": False}, mid))
    for params, f in cases:
        ok, mm = one(df, params, f)
        allok &= ok
        msgs.append(mm)
    return allok, " | ".join(msgs)
