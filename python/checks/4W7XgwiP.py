"""Independent check — Confluence Engine Strategy [JOAT] (4W7XgwiP): 5-minute bars (24 h synthetic) on a US stock chart (60-minute periods counted from 09:30 New York), market orders at the next open, commission / slippage / margin off (the sizing is a percent of equity, which does not change the trade prices).
Signal bar: linreg(close) crossing its signal SMA, EMA fast/slow trend, 60-minute EMA bias (period closes, lookahead off), volume spike, RSI cap, ATR(14)/ATR(50) trending regime, a 0-100 confluence score and a cooldown after the last exit; one position at a time.
Fill bar: the ATR at the fill bar sets TP / SL around the average entry price, the exit order is issued from the NEXT bar (position open at script time); a timeout (bars since the fill) and an EMA trend flip close the trade at the next open. Uses the pending-order reference broker (simulate_ord).
Variants: defaults; shorter linreg/EMAs, a tighter regime filter off, wider SL/TP; long only with a short cooldown and timeout 8, volume filter off."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, np_periods, np_rsi, np_security_lookahead_off, np_sma, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "4W7XgwiP"
MINTICK = 0.01


def linreg(x, n):
    out = np.full(len(x), np.nan)
    xs = np.arange(n, dtype=float)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        if np.isnan(w).any():
            continue
        s, b = np.polyfit(xs, w, 1)
        out[i] = b + s * (n - 1)
    return out


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    lr = linreg(c, p["lr"])
    sig = np_sma(lr, p["sig"])
    fe, se = np_ema(c, p["fast"]), np_ema(c, p["slow"])
    atr14, atrs = np_atr(h, l, c, 14), np_atr(h, l, c, p["reg"])
    rsi = np_rsi(c, 14)
    vsma = np_sma(v, p["vl"])
    pid, last_of = np_periods(df, 60)
    pc = c[last_of]
    hf = np_security_lookahead_off(np_ema(pc, p["fast"]), pid, last_of)
    hs = np_security_lookahead_off(np_ema(pc, p["slow"]), pid, last_of)
    warm = max(p["slow"] * 2, p["reg"] * 2)
    S = dict(prev=0, lastexit=None, eatr=np.nan, ebar=None, inl=False, ins=False, tp=np.nan, sl=np.nan)

    def orders(i, pos, info):
        out = []
        with np.errstate(invalid="ignore"):
            den = max(atrs[i], MINTICK) if not np.isnan(atrs[i]) else np.nan
            ratio = atr14[i] / den if (not np.isnan(den) and den != 0) else 0.0
            trending = ratio > p["thr"] or not p["rf"]
            tu, td = fe[i] > se[i], fe[i] < se[i]
            hb, hr = hf[i] > hs[i], hf[i] < hs[i]
            volok = (not p["vf"]) or v[i] > vsma[i] * p["vm"]
            crs = i > 0 and lr[i] > sig[i] and lr[i - 1] <= sig[i - 1]
            crd = i > 0 and lr[i] < sig[i] and lr[i - 1] >= sig[i - 1]
            vs = 20 if v[i] > vsma[i] * 1.2 else (10 if v[i] > vsma[i] else 0)
            reg = 15 if trending else 0
            ls = int(min((25 if tu else 0) + (20 if hb else 0) + vs + int(min((55.0 - rsi[i]) * 0.5, 20.0) if rsi[i] < 50 else 0.0) + reg, 100)) if crs else 0
            ss = int(min((25 if td else 0) + (20 if hr else 0) + vs + int(min((rsi[i] - 45.0) * 0.5, 20.0) if rsi[i] > 50 else 0.0) + reg, 100)) if crd else 0
            ready = i >= warm
            bull = bool(crs and tu and hb and volok and rsi[i] < 72 and trending and ls >= p["score"] and p["longs"] and ready)
            bear = bool(crd and td and hr and volok and rsi[i] > 28 and trending and ss >= p["score"] and p["shorts"] and ready)
        cd = S["lastexit"] is None or i - S["lastexit"] >= p["cool"]
        if pos > 0 and S["prev"] == 0:
            S["inl"], S["ins"], S["eatr"], S["ebar"] = True, False, atr14[i], i
        if pos < 0 and S["prev"] == 0:
            S["ins"], S["inl"], S["eatr"], S["ebar"] = True, False, atr14[i], i
        if pos == 0 and S["prev"] != 0:
            S["inl"] = S["ins"] = False
            S["lastexit"] = i
        if S["inl"] and not np.isnan(S["eatr"]):
            S["tp"], S["sl"] = info["ep"] + S["eatr"] * p["tpm"], info["ep"] - S["eatr"] * p["slm"]
        if S["ins"] and not np.isnan(S["eatr"]):
            S["tp"], S["sl"] = info["ep"] - S["eatr"] * p["tpm"], info["ep"] + S["eatr"] * p["slm"]
        if bull and cd and pos == 0:
            out.append(("entry", "Long", 1, None, None))
        if bear and cd and pos == 0:
            out.append(("entry", "Short", -1, None, None))
        if S["inl"] and not np.isnan(S["tp"]):
            out.append(("exit", "TP/SL Long", "Long", S["sl"], S["tp"]))
        if S["ins"] and not np.isnan(S["tp"]):
            out.append(("exit", "TP/SL Short", "Short", S["sl"], S["tp"]))
        if S["inl"] and i - S["ebar"] >= p["to"]:
            out.append(("close", "Long"))
        if S["ins"] and i - S["ebar"] >= p["to"]:
            out.append(("close", "Short"))
        with np.errstate(invalid="ignore"):
            if S["inl"] and td:
                out.append(("close", "Long"))
            if S["ins"] and tu:
                out.append(("close", "Short"))
        S["prev"] = pos
        return out

    ref = simulate_ord(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(lr=9, sig=5, fast=20, slow=50, reg=50, score=50, longs=True, shorts=True, vf=True, vl=20, vm=1.0, cool=3, rf=True, thr=0.85, slm=1.5, tpm=2.5, to=20)


def check():
    df = bars(30000, seed=77, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    cases = (({}, {}),
             ({"LR Length": 6, "Fast EMA": 12, "Slow EMA": 30, "Regime Filter (no ranging)": False, "SL  (ATR x)": 2.0, "TP  (ATR x)": 3.0},
              dict(lr=6, fast=12, slow=30, rf=False, slm=2.0, tpm=3.0)),
             ({"Trade Short": False, "Cooldown Bars After Exit": 1, "Timeout Exit (bars)": 8, "Require Volume Spike": False},
              dict(shorts=False, cool=1, to=8, vf=False)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
