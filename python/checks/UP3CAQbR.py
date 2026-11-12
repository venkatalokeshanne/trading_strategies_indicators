"""Independent check — Crucible Convergence Engine [JOAT] (UP3CAQbR): daily bars scaled around 20000, market orders at the signal close (process_orders_on_close). Regime: ATR percent-rank over the previous bars (> turbulence = volatile, > kinetic = trending), directional-movement bias (EMA of up-moves vs down-moves) and EMA(8/34) distance in ATR, raw regime confirmed over two bars. Trend = fast vs slow MA, momentum = EMA5 of (EMA fast - EMA slow) of price change x log(1 + volume ratio x gain) vs its EMA12 signal, a 2-sigma SMA band, a volume gate; the first bar all agree enters with an ATR stop / target at the close. Closes: trailing shield (max of close - k ATR), regime flip, band extreme, rounded price rails. Uses the pending-order reference broker (simulate_ord) with on_close.
Variants: defaults; softer regime thresholds with SMA filaments and 500 rails; regime gate off, no volume gate, 100 rails; tighter stops without the trail."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_sma, run_conversion, simulate_ord

TV_ID = "UP3CAQbR"


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


def prank(x, n):
    out = np.full(len(x), np.nan)
    for i in range(n, len(x)):
        if not np.isnan(x[i]):
            w = x[i - n:i]
            out[i] = 100.0 * np.sum(w <= x[i]) / n
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    nz = lambda a: np.where(np.isnan(a), 0.0, a)
    with np.errstate(invalid="ignore", divide="ignore"):
        ratr = np_atr(h, l, c, p["ratr"])
        pct = prank(ratr, p["rank"])
        h1, l1 = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
        up, dn = np.fmax(h - h1, 0.0), np.fmax(l1 - l, 0.0)
        up = np.where(np.isnan(h - h1), np.nan, up)
        dn = np.where(np.isnan(l1 - l), np.nan, dn)
        sp = ema_na(np.where(up > dn, up, 0.0), p["ratr"])
        sm = ema_na(np.where(dn > up, dn, 0.0), p["ratr"])
        tot = sp + sm
        dirb = np.where(tot != 0, (sp - sm) / tot, 0.0)
        emab = np.where(ratr != 0, (ema_na(c, 8) - ema_na(c, 34)) / ratr, 0.0)
        vol_ = pct > p["vol"]
        trd = (pct > p["trd"]) & ~vol_
        bull = (dirb > 0.1) & (emab > 0.5)
        bear = (dirb < -0.1) & (emab < -0.5)
        raw = np.where(vol_, 2, np.where(trd & bull, 1, np.where(trd & bear, -1, 0)))
        reg = np.zeros(n, int)
        pend, cnt, cur = 0, 0, 0
        for i in range(n):
            if raw[i] == pend:
                cnt += 1
            else:
                pend, cnt = raw[i], 1
            if cnt >= 2:
                cur = pend
            reg[i] = cur
        mk = np_sma if p["ma"] == "SMA" else ema_na
        ef, es = mk(c, p["tf"]), mk(c, p["ts"])
        tb, tbear = ef > es, ef < es
        vr = np_sma(v, 3) / np_sma(v, 14)
        chg = np.r_[np.nan, np.diff(c)]
        vwm = chg * np.log(1 + vr * 1.5)
        mf, ms = ema_na(vwm, p["mf"]), ema_na(vwm, p["ms"])
        midx = ema_na(mf - ms, 5)
        msig = ema_na(midx, 12)
        mbull, mbear = midx > msig, midx < msig
        bm = np_sma(c, 100)
        bd = pd.Series(c).rolling(100).std(ddof=0).to_numpy()
        bup, bdn = bm + 2.0 * bd, bm - 2.0 * bd
        e21 = ema_na(c, 21)
        top = p["round"] * np.ceil(e21 / p["round"])
        bot = p["round"] * np.floor(e21 / p["round"])
        tol = (top - bot) * 0.15
        vg = np.where(np_sma(v, 14) != 0, np_sma(v, 3) / np_sma(v, 14), 1.0)
        vgok = (vg >= p["vgate"]) if p["usevg"] else np.ones(n, bool)
        regok = ((reg == 1) | (reg == -1)) if p["usereg"] else np.ones(n, bool)
        lconv = regok & tb & mbull & (c < bup) & vgok & ((reg == 1) if p["usereg"] else True)
        sconv = regok & tbear & mbear & (c > bdn) & vgok & ((reg == -1) if p["usereg"] else True)
        atr = np_atr(h, l, c, 14)
    lprev = np.r_[False, lconv[:-1]]
    sprev = np.r_[False, sconv[:-1]]
    S = dict(trail=np.nan)

    def orders(i, pos):
        out = []
        with np.errstate(invalid="ignore"):
            a = atr[i]
            sd, td, trd_ = a * p["stopm"], a * p["tpm"], a * 1.5
            if pos > 0:
                nt = c[i] - trd_
                if p["trail"]:
                    S["trail"] = nt if np.isnan(S["trail"]) else max(S["trail"], nt)
            elif pos < 0:
                nt = c[i] + trd_
                if p["trail"]:
                    S["trail"] = nt if np.isnan(S["trail"]) else min(S["trail"], nt)
            else:
                S["trail"] = np.nan
            if lconv[i] and not lprev[i]:
                out.append(("entry", "Long", 1, None, None))
                out.append(("exit", "Long X", "Long", c[i] - sd, c[i] + td))
                S["trail"] = np.nan
            if sconv[i] and not sprev[i]:
                out.append(("entry", "Short", -1, None, None))
                out.append(("exit", "Short X", "Short", c[i] + sd, c[i] - td))
                S["trail"] = np.nan
            if p["trail"] and not np.isnan(S["trail"]):
                if pos > 0 and l[i] <= S["trail"]:
                    out.append(("close", "Long"))
                if pos < 0 and h[i] >= S["trail"]:
                    out.append(("close", "Short"))
            if pos > 0 and reg[i] == -1:
                out.append(("close", "Long"))
            if pos < 0 and reg[i] == 1:
                out.append(("close", "Short"))
            if pos > 0 and c[i] >= bup[i]:
                out.append(("close", "Long"))
            if pos < 0 and c[i] <= bdn[i]:
                out.append(("close", "Short"))
            if pos > 0 and top[i] - tol[i] <= h[i] <= top[i] + tol[i]:
                out.append(("close", "Long"))
            if pos < 0 and bot[i] - tol[i] <= l[i] <= bot[i] + tol[i]:
                out.append(("close", "Short"))
        return out

    ref = simulate_ord(o, h, l, c, orders, on_close=True)
    ok, d = compare(run_conversion(TV_ID, df, params=params, strategy_overrides={"commission_value": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(ratr=14, rank=50, vol=70, trd=55, ma="EMA", tf=8, ts=34, mf=8, ms=21, round=500.0, usereg=True, usevg=True, vgate=1.1,
            stopm=2.0, tpm=3.0, trail=True)


def check():
    df = bars(3000, seed=77)
    for k in ("open", "high", "low", "close"):
        df[k] = 20000 * (df[k] / 100) ** 0.35
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Kinetic Threshold": 35, "Turbulence Threshold": 90, "Filament Type": "SMA"}, dict(trd=35, vol=90, ma="SMA")),
             ({"Regime Gate Active": False, "Require Volume Confirmation": False, "Grid Increment": 100.0}, dict(usereg=False, usevg=False, round=100.0)),
             ({"Shield Multiple": 1.0, "Objective Multiple": 1.5, "Trailing Shield": False, "Kinetic Threshold": 40, "Volume Gate Threshold": 0.9},
              dict(stopm=1.0, tpm=1.5, trail=False, trd=40, vgate=0.9)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
