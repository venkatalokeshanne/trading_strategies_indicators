"""Independent check — Auto Fib + EMA200 MTF [SamoAlgo] FIXED (VxbMvF97): 1-minute bars (24 h synthetic) on a US stock chart (higher-timeframe periods counted from 09:30 New York), orders processed at the signal bar's close (process_orders_on_close), commission / slippage / margin off (quantity only needs to be positive).
Last two confirmed pivots (left-strict, right non-strict, strength 2) form a swing; the setup is armed when swing > ATR x multiple, flat and not the same traded swing, and expires after N bars (the age counts from the arming bar). A trigger needs the setup armed, the 1 / 5 / 15 / 60-minute EMA agreement (period closes, lookahead off), session (open time inside 08:00-21:00 New York),
ADX, cooldown, trades-per-day (day / month change in New York time), the close beyond the fib entry level and the minimum R:R (ATR bracket or fib / fixed R:R from the close); entry and the exit bracket are issued together at the close. Uses the pending-order reference broker (simulate_ord, on_close).
Variants: defaults (EMA 457); EMA 20, 3 timeframes agreeing, no session / ADX, cooldown 3; fib stop / target with fixed R:R 2, buffer 0.5 ATR, volatility filter on, max 1 trade per day, longs only."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_dmi, np_ema, np_periods, np_security_lookahead_off, np_sma, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "VxbMvF97"


def piv(x, ln, high):
    out = np.full(len(x), np.nan)
    for i in range(2 * ln, len(x)):
        w = x[i - 2 * ln:i + 1]
        ctr = w[ln]
        a, b = w[:ln], w[ln + 1:]
        if (high and (a < ctr).all() and (b <= ctr).all()) or ((not high) and (a > ctr).all() and (b >= ctr).all()):
            out[i] = ctr
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    dom, mon = ny.dt.day.to_numpy(), ny.dt.month.to_numpy()
    atr = np_atr(h, l, c, 14)
    atravg = np_sma(atr, 50)
    adx = np_dmi(h, l, c, p["adxl"])[2]
    ph, pl = piv(h, 2, True), piv(l, 2, False)
    emas = []
    for tf in (1, 5, 15, 60):
        pid, last_of = np_periods(df, tf)
        emas.append(np_security_lookahead_off(np_ema(c[last_of], p["el"]), pid, last_of))
    S = dict(td=0, ltd=None, lph=np.nan, lphb=np.nan, lpl=np.nan, lplb=np.nan, ltb=None, ltph=None, ltpl=None,
             la=False, lage=0, lentry=np.nan, lstop=np.nan, ltgt=np.nan, sa=False, sage=0, sentry=np.nan, sstop=np.nan, stgt=np.nan)

    def orders(i, pos):
        out = []
        with np.errstate(invalid="ignore", divide="ignore"):
            above = sum(1 for e in emas if c[i] > e[i])
            below = sum(1 for e in emas if c[i] < e[i])
            lt_ok = (not p["ef"]) or above >= p["agree"]
            st_ok = (not p["ef"]) or below >= p["agree"]
            vol_ok = (not p["vf"]) or atr[i] > atravg[i] * 0.3
            insess = (not p["sess"]) or (480 <= mins[i] < 1260)
            adx_ok = (not p["adxf"]) or adx[i] > 20
            if S["ltd"] is None or dom[i] != dom[i - 1] or mon[i] != mon[i - 1]:
                S["td"], S["ltd"] = 0, dom[i]
            mt_ok = (not p["mtf"]) or S["td"] < p["mt"]
            if not np.isnan(ph[i]):
                S["lph"], S["lphb"] = ph[i], i - 2
            if not np.isnan(pl[i]):
                S["lpl"], S["lplb"] = pl[i], i - 2
            cd_ok = S["ltb"] is None or i - S["ltb"] >= p["cool"]
            nl = (not p["same"]) or S["ltpl"] is None or S["lplb"] != S["ltpl"]
            ns = (not p["same"]) or S["ltph"] is None or S["lphb"] != S["ltph"]
            flat = pos == 0
            swing = S["lph"] - S["lpl"]
            if p["long"] and not np.isnan(S["lpl"]) and not np.isnan(S["lph"]) and S["lplb"] < S["lphb"] and not S["la"] and flat and nl:
                if swing > atr[i] * 3.8 and swing > 0:
                    S["lentry"] = S["lpl"] + swing * 0.7
                    S["lstop"] = S["lpl"] - atr[i] * p["buf"]
                    S["ltgt"] = np.nan if p["rr"] else S["lpl"] + swing * 1.618
                    S["lage"], S["la"] = 0, True
            if p["short"] and not np.isnan(S["lph"]) and not np.isnan(S["lpl"]) and S["lphb"] < S["lplb"] and not S["sa"] and flat and ns:
                if swing > atr[i] * 3.8 and swing > 0:
                    S["sentry"] = S["lph"] - swing * 0.7
                    S["sstop"] = S["lph"] + atr[i] * p["buf"]
                    S["stgt"] = np.nan if p["rr"] else S["lph"] - swing * 1.618
                    S["sage"], S["sa"] = 0, True
            if S["la"]:
                S["lage"] += 1
                S["la"] = S["lage"] <= 33
            if S["sa"]:
                S["sage"] += 1
                S["sa"] = S["sage"] <= 33
            if p["atrx"]:
                sll, tpl, sls, tps = c[i] - atr[i] * 3, c[i] + atr[i] * 5, c[i] + atr[i] * 3, c[i] - atr[i] * 5
            else:
                sll = S["lstop"]
                tpl = c[i] + (c[i] - S["lstop"]) * 2.0 if p["rr"] else S["ltgt"]
                sls = S["sstop"]
                tps = c[i] - (S["sstop"] - c[i]) * 2.0 if p["rr"] else S["stgt"]
            rrl = (tpl - c[i]) / abs(c[i] - sll) if abs(c[i] - sll) > 0 else np.nan
            rrs = (c[i] - tps) / abs(sls - c[i]) if abs(sls - c[i]) > 0 else np.nan
            rl_ok = (not p["rrf"]) or rrl >= 1.5
            rs_ok = (not p["rrf"]) or rrs >= 1.5
            lt = S["la"] and lt_ok and vol_ok and insess and c[i] > S["lentry"] and flat and cd_ok and adx_ok and mt_ok and rl_ok
            stg = S["sa"] and st_ok and vol_ok and insess and c[i] < S["sentry"] and flat and cd_ok and adx_ok and mt_ok and rs_ok
        if lt:
            out.append(("entry", "L", 1, None, None))
            out.append(("exit", "L-x", "L", sll, tpl))
            S["la"], S["ltb"], S["ltpl"] = False, i, S["lplb"]
            S["td"] += 1
        if stg:
            out.append(("entry", "S", -1, None, None))
            out.append(("exit", "S-x", "S", sls, tps))
            S["sa"], S["ltb"], S["ltph"] = False, i, S["lphb"]
            S["td"] += 1
        return out

    ref = simulate_ord(o, h, l, c, orders, on_close=True)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="1", params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(el=457, agree=4, ef=True, vf=False, sess=True, adxf=True, adxl=14, mtf=True, mt=2, cool=7, same=True, rrf=True, buf=0.0, rr=False, atrx=True, long=True, short=True)


def check():
    msgs, allok = [], True
    cases = ((60000, 31, {}, {}),
             (20000, 32, {"EMA length": 20, "Min timeframes agreeing (out of 4)": 3, "Session filter (London + NY only)": False, "ADX trend-strength filter": False, "Cooldown — min bars between trades": 3},
              dict(el=20, agree=3, sess=False, adxf=False, cool=3)),
             (20000, 33, {"EMA length": 20, "Use ATR stop & target (instead of fib)": False, "Use fixed R:R instead of 1.618 target": True, "Stop buffer beyond level 0 (x ATR)": 0.5,
                          "Volatility filter (avoid dead market)": True, "Max trades per day": 1, "Allow Shorts": False, "Min timeframes agreeing (out of 4)": 2},
              dict(el=20, agree=2, atrx=False, rr=True, buf=0.5, vf=True, mt=1, short=False)))
    for nb, seed, params, ov in cases:
        df = bars(nb, seed=seed, freq="1min")
        for k in ("open", "high", "low", "close"):
            df[k] = 100 * (df[k] / 100) ** 0.1
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
