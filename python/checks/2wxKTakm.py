"""Independent check — DearmasTrader Pro V4 Multi-Strategy (2wxKTakm): daily bars, market orders at the next open, slippage / commission / margin off. Entry engines: zero-lag EMA (src crosses ZLEMA +/- k ATR with a rising / falling ZLEMA), Bollinger breakout, RSI pivot divergence (the pivot low's RSI higher and price lower than at the previous pivot, evaluated at the confirmation bar), MACD signal cross, "Magical DCA shield" (macro EMA, ZLEMA cross, RSI limit). Exit engines: ZLEMA cross, Bollinger trailing stop (ratcheted from the close, ATR x multiple, only while the position is open at script time), RSI 70/30 cross, MACD cross, structural floor / ceiling or macro EMA crash. Optional trend and volume filters, direction restriction, panic button. The entry issues the stop / limit exit (ATR or percentage, either may be absent) from the signal close; signal exits close at the next open. Uses the pending-order reference broker (simulate_ord).
Variants: zero lag in and out (defaults); Bollinger with trailing exit and percentage stop only; RSI divergence long only with a percentage target only; MACD in with magic exit plus trend and volume filters; magic in, MACD out, short only, ATR stop and no target; panic button on."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_rsi, np_sma, run_conversion, simulate_ord

TV_ID = "2wxKTakm"


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


def cu(a, b):
    pa, pb = np.r_[np.nan, a[:-1]], np.r_[np.nan, b[:-1]]
    with np.errstate(invalid="ignore"):
        return (a > b) & (pa <= pb)


def cd(a, b):
    pa, pb = np.r_[np.nan, a[:-1]], np.r_[np.nan, b[:-1]]
    with np.errstate(invalid="ignore"):
        return (a < b) & (pa >= pb)


def pivots(x, left, right, high):
    out = np.full(len(x), False)
    for i in range(left + right, len(x)):
        w = x[i - left - right:i + 1]
        if np.isnan(w).any():
            continue
        ctr = w[left]
        a, b = w[:left], w[left + 1:]
        out[i] = ((a < ctr).all() and (b <= ctr).all()) if high else ((a > ctr).all() and (b >= ctr).all())
    return out


def rwin(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    e1 = np_ema(c, 20)
    zl = 2 * e1 - ema_na(e1, 20)
    atr = np_atr(h, l, c, 14)
    uz, lz = zl + atr * 2.0, zl - atr * 2.0
    zl1 = np.r_[np.nan, zl[:-1]]
    with np.errstate(invalid="ignore"):
        z_long = cu(c, uz) & (zl > zl1)
        z_short = cd(c, lz) & (zl < zl1)
    z_xl, z_xs = cd(c, zl), cu(c, zl)
    mid = np_sma(c, 20)
    sd = pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    bbu, bbl = mid + 2.0 * sd, mid - 2.0 * sd
    bb_long, bb_short = cu(c, bbu), cd(c, bbl)
    rsi = np_rsi(c, 14)
    ppl, pph = pivots(rsi, 5, 5, False), pivots(rsi, 5, 5, True)
    rl = np.zeros(n, bool)
    rs = np.zeros(n, bool)
    bp = (np.nan, np.nan)
    sp = (np.nan, np.nan)
    for i in range(10, n):
        if ppl[i]:
            pv, ps = rsi[i - 5], c[i - 5]
            rl[i] = bool(pv > bp[0] and ps < bp[1])
            bp = (pv, ps)
        if pph[i]:
            pv, ps = rsi[i - 5], c[i - 5]
            rs[i] = bool(pv < sp[0] and ps > sp[1])
            sp = (pv, ps)
    rx_l, rx_s = cu(rsi, np.full(n, 70.0)), cd(rsi, np.full(n, 30.0))
    ml = np_ema(c, 12) - np_ema(c, 26)
    ms = ema_na(ml, 9)
    m_long, m_short = cu(ml, ms), cd(ml, ms)
    macro = np_ema(c, 200)
    floor_, ceil_ = rwin(l, 50, np.min), rwin(h, 50, np.max)
    with np.errstate(invalid="ignore"):
        mg_long = (c > macro) & cu(c, zl) & (rsi < 65)
        mg_short = (c < macro) & cd(c, zl) & (rsi > 35)
    mc_l = cd(c, floor_) | cd(c, macro)
    mc_s = cu(c, ceil_) | cu(c, macro)
    tema = np_ema(c, p["tlen"])
    vema = np_ema(v, 20)
    with np.errstate(invalid="ignore"):
        tok_l = (c > tema) if p["trend"] else np.ones(n, bool)
        tok_s = (c < tema) if p["trend"] else np.ones(n, bool)
        vok = (v >= vema * 1.0) if p["vol"] else np.ones(n, bool)
    can_l = (p["dir"] != "Short Only") & tok_l & vok
    can_s = (p["dir"] != "Long Only") & tok_s & vok
    E = {"z": (z_long, z_short), "bb": (bb_long, bb_short), "rsi": (rl, rs), "macd": (m_long, m_short), "magic": (mg_long, mg_short), "off": (np.zeros(n, bool), np.zeros(n, bool))}
    el, es = E[p["entry"]]
    S = dict(ts=np.nan, pts=np.nan)
    nn = lambda x: None if np.isnan(x) else x

    def levels(i, side):
        if side > 0:
            sl = c[i] - atr[i] * 2.0 if p["sl"] == "atr" else (c[i] * (1 - 1.5 / 100) if p["sl"] == "pct" else np.nan)
            tp = c[i] + atr[i] * 4.0 if p["tp"] == "atr" else (c[i] * (1 + 3.0 / 100) if p["tp"] == "pct" else np.nan)
        else:
            sl = c[i] + atr[i] * 2.0 if p["sl"] == "atr" else (c[i] * (1 + 1.5 / 100) if p["sl"] == "pct" else np.nan)
            tp = c[i] - atr[i] * 4.0 if p["tp"] == "atr" else (c[i] * (1 - 3.0 / 100) if p["tp"] == "pct" else np.nan)
        return sl, tp

    def orders(i, pos):
        out = []
        prev_ts = S["ts"]
        with np.errstate(invalid="ignore"):
            if pos > 0:
                ns = c[i] - atr[i] * 3.0
                S["ts"] = ns if np.isnan(S["ts"]) else max(ns, S["ts"])
            elif pos < 0:
                ns = c[i] + atr[i] * 3.0
                S["ts"] = ns if np.isnan(S["ts"]) else min(ns, S["ts"])
            else:
                S["ts"] = np.nan
            ts = S["ts"]
            pc = c[i - 1] if i else np.nan
            xdn = c[i] < ts and pc >= prev_ts
            xup = c[i] > ts and pc <= prev_ts
            bxl = p["trail"] and pos > 0 and not np.isnan(ts) and xdn
            bxs = p["trail"] and pos < 0 and not np.isnan(ts) and xup
        X = {"z": (z_xl[i], z_xs[i]), "bb": (bxl, bxs), "rsi": (rx_l[i], rx_s[i]), "macd": (cd(ml, ms)[i], cu(ml, ms)[i]), "magic": (mc_l[i], mc_s[i]), "off": (False, False)}
        xl, xs = X[p["exit"]]
        if p["panic"]:
            out.append(("close_all",))
        if el[i] and can_l[i] and not p["panic"]:
            sl, tp = levels(i, 1)
            out.append(("entry", "Long", 1, None, None))
            if not (np.isnan(sl) and np.isnan(tp)):
                out.append(("exit", "Long SL/TP", "Long", nn(sl), nn(tp)))
        if es[i] and can_s[i] and not p["panic"]:
            sl, tp = levels(i, -1)
            out.append(("entry", "Short", -1, None, None))
            if not (np.isnan(sl) and np.isnan(tp)):
                out.append(("exit", "Short SL/TP", "Short", nn(sl), nn(tp)))
        if p["exit"] != "off" and not p["panic"]:
            if xl and pos > 0:
                out.append(("close", "Long"))
            if xs and pos < 0:
                out.append(("close", "Short"))
        return out

    ref = simulate_ord(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > (8 if not p["panic"] else -1), f"{d} (got {len(ref)})"


BASE = dict(entry="z", exit="z", sl="atr", tp="atr", trail=True, trend=False, vol=False, dir="Bidirectional", panic=False, tlen=200)


def check():
    df = bars(4000, seed=777)
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.6
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Estrategia de ENTRADA": "Bollinger + ATR", "Estrategia de SALIDA": "Bollinger + ATR", "Tipo de Stop Loss": "Porcentaje", "Tipo de Take Profit": "Ninguno"},
              dict(entry="bb", exit="bb", sl="pct", tp="none")),
             ({"Estrategia de ENTRADA": "RSI Divergence", "Estrategia de SALIDA": "RSI Divergence", "Dirección de Trading": "Long Only", "Tipo de Stop Loss": "Ninguno",
               "Tipo de Take Profit": "Porcentaje"},
              dict(entry="rsi", exit="rsi", dir="Long Only", sl="none", tp="pct")),
             ({"Estrategia de ENTRADA": "MACD / SMA Cross", "Estrategia de SALIDA": "Magical DCA Shield", "Filtro de Tendencia EMA": True, "Filtro de Volumen Mínimo": True,
               "EMA Tendencia (periodos)": 100},
              dict(entry="macd", exit="magic", trend=True, vol=True, tlen=100)),
             ({"Estrategia de ENTRADA": "Magical DCA Shield", "Estrategia de SALIDA": "MACD / SMA Cross", "Dirección de Trading": "Short Only", "Tipo de Take Profit": "Ninguno"},
              dict(entry="magic", exit="macd", dir="Short Only", tp="none")),
             ({"🔥 BOTÓN DE PÁNICO (CIERRE INMEDIATO)": True}, dict(panic=True)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
