"""Independent check — Universal Aggressive Trend MACD v3.3 (UVosPbFA): daily bars, market orders at the signal close (process_orders_on_close), margin / commission off. While flat: trend EMA filter (close beyond the EMA and the EMA higher / lower than `slope` bars ago), ADX(dmi) filter, volume filter, entry cool-down, and a trigger = a MACD cross armed for N bars (MACD still on the right side) or a breakout of the previous N-bar high / low with the MACD histogram agreeing. The emergency ATR stop is issued only while the trade is open at script time (works from the bar after the entry bar, from the entry bar's close); the peak-profit % (at closes, from the average entry price) arms the trailing take-profit at a minimum and closes the trade when the profit falls to peak x (1 - giveback %) or peak - giveback points; an optional opposite MACD cross closes too. Uses the pending-order reference broker (simulate_ord, on_close).
Variants: defaults; points mode with opposite-cross exit and no arming; long only with no slope / ADX filter and a tight ATR stop."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_dmi, np_ema, np_sma, run_conversion, simulate_ord

TV_ID = "UVosPbFA"


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    macd = np_ema(c, p["fast"]) - np_ema(c, p["slow"])
    sig = np_ema(macd, p["sig"])
    hist = macd - sig
    tema = np_ema(c, 99)
    adx = np_dmi(h, l, c, p["adxl"])[2]
    vsma = np_sma(v, 22)
    atr = np_atr(h, l, c, 18)
    with np.errstate(invalid="ignore"):
        pm, ps = np.r_[np.nan, macd[:-1]], np.r_[np.nan, sig[:-1]]
        bull = (macd > sig) & (pm <= ps)
        bear = (macd < sig) & (pm >= ps)
    hb = np.full(n, np.nan)
    lb = np.full(n, np.nan)
    for i in range(p["cont"] + 1, n):
        hb[i] = h[i - p["cont"]:i].max()
        lb[i] = l[i - p["cont"]:i].min()
    S = dict(lb=None, lr=None, le=None, peak=np.nan, armed=False)

    def orders(i, pos, info):
        out = []
        if bull[i]:
            S["lb"] = i
        if bear[i]:
            S["lr"] = i
        with np.errstate(invalid="ignore"):
            sl_up = (not p["slope"]) or tema[i] > (tema[i - 3] if i >= 3 else np.nan)
            sl_dn = (not p["slope"]) or tema[i] < (tema[i - 3] if i >= 3 else np.nan)
            ltr = c[i] > tema[i] and sl_up
            st_ = c[i] < tema[i] and sl_dn
            mok = ((not p["useadx"]) or adx[i] > 20.0) and v[i] > vsma[i] * 0.6
            bfr = (not p["arm"]) or (S["lb"] is not None and i - S["lb"] <= 10 and macd[i] > sig[i])
            sfr = (not p["arm"]) or (S["lr"] is not None and i - S["lr"] <= 10 and macd[i] < sig[i])
            lco = macd[i] > sig[i] and hist[i] > 0 and c[i] > hb[i]
            sco = macd[i] < sig[i] and hist[i] < 0 and c[i] < lb[i]
            cd = S["le"] is None or i - S["le"] >= 3
            flat = pos == 0
            lc = p["longs"] and flat and cd and mok and ltr and (bfr or lco)
            scn = p["shorts"] and flat and cd and mok and st_ and (sfr or sco)
            cur = 0.0
            ep = info.get("ep", np.nan)
            if pos > 0 and ep > 0:
                cur = (c[i] - ep) / ep * 100.0
            if pos < 0 and ep > 0:
                cur = (ep - c[i]) / ep * 100.0
            if flat:
                S["peak"] = np.nan
                S["armed"] = False
                S["lstop"] = np.nan
                S["sstop"] = np.nan
            if not flat:
                S["peak"] = cur if np.isnan(S["peak"]) else max(S["peak"], cur)
                if S["peak"] >= 0.5:
                    S["armed"] = True
            lvl = np.nan
            if S["armed"] and not np.isnan(S["peak"]):
                lvl = S["peak"] * (1 - p["give"] / 100.0) if p["mode"] == "rel" else S["peak"] - p["give"]
            tx = S["armed"] and not np.isnan(lvl) and cur <= lvl
            if pos > 0 and tx:
                out.append(("close", "Long"))
            if pos < 0 and tx:
                out.append(("close", "Short"))
            if p["opp"] and pos > 0 and bear[i]:
                out.append(("close", "Long"))
            if p["opp"] and pos < 0 and bull[i]:
                out.append(("close", "Short"))
            if lc:
                out.append(("entry", "Long", 1, None, None))
                S.update(lstop=c[i] - atr[i] * p["em"], sstop=np.nan, peak=np.nan, armed=False, le=i)
            if scn:
                out.append(("entry", "Short", -1, None, None))
                S.update(sstop=c[i] + atr[i] * p["em"], lstop=np.nan, peak=np.nan, armed=False, le=i)
            if pos > 0 and not np.isnan(S.get("lstop", np.nan)):
                out.append(("exit", "Long Emergency SL", "Long", S["lstop"], None))
            if pos < 0 and not np.isnan(S.get("sstop", np.nan)):
                out.append(("exit", "Short Emergency SL", "Short", S["sstop"], None))
        return out

    ref = simulate_ord(o, h, l, c, orders, on_close=True)
    ok, d = compare(run_conversion(TV_ID, df, params=params, strategy_overrides={"commission_value": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(fast=14, slow=39, sig=9, arm=True, cont=5, longs=True, shorts=True, slope=True, adxl=11, useadx=True, em=2.5, opp=False, mode="rel", give=3.0)


def check():
    df = bars(3000, seed=91)
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Trailing TP Modus": "Prozentpunkte", "Rücklauf vom höchsten Profit": 1.5, "Bei MACD-Gegencross schließen": True, "MACD Cross Arming nutzen": False},
              dict(mode="pts", give=1.5, opp=True, arm=False)),
             ({"Shorts erlauben": False, "EMA-Slope Filter nutzen": False, "ADX Filter nutzen": False, "ATR Emergency Stop Multiplier": 1.0, "MACD Fast Length": 10,
               "ADX Smoothing": 14, "Continuation Breakout Lookback": 8},
              dict(shorts=False, slope=False, useadx=False, em=1.0, fast=10, adxl=14, cont=8)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
