"""Independent check — CleightyP BOS/SMA/MACD/VWAP (YYABPdUo): hourly bars of a 24 h market (UTC), margin / commission / slippage off. Pivot structure (left-strict pivots of lookback 2 on the 1 h chart unless auto-adjust is off), SMA 21/84/252 slope filter modes (+ stacking / slope divergence options), optional NY / daily anchored VWAP filters (ohlc4 x volume, reset at the anchor time of the bar's date in the chosen zone). With "Enter On Tick" a buy-stop at the last pivot high (sell-stop at the low) is renewed or cancelled every bar (pivot not already used, BOS / CHoCH selection, trades-per-day limit); otherwise a market order follows a confirmed close beyond the pivot (strong-candle test). Stop = previous swing (a percentage of the distance from the entry to the swing) / entry candle / percent (+ buffers) and target = R:R x risk, with sanity checks (stop below target below / above the entry), a trade-direction switch and an optional trading window; the exit is issued while the trade is open at script time (an insane pair closes the trade instead); the day change can close the position, cancel pending orders and clear levels / structure. Uses the pending-order reference broker (simulate_ord).
Variants: defaults (on tick); market entries with the strong-candle test, entry-candle stop and buffer; percent stop with CHoCH-only, separate R:R, SMA-21-only, day limits, EOD close and daily structure reset with lookback 1; both VWAP filters with price-vs-SMA mode."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_sma, run_conversion, simulate_ord

TV_ID = "YYABPdUo"


def pivots(x, ln, high):
    out = np.full(len(x), False)
    for i in range(2 * ln, len(x)):
        w = x[i - 2 * ln:i + 1]
        ctr = w[ln]
        a, b = w[:ln], w[ln + 1:]
        out[i] = ((a < ctr).all() and (b <= ctr).all()) if high else ((a > ctr).all() and (b >= ctr).all())
    return out


def vwap_series(df, src, v, anchor_tz, hh, mm):
    n = len(src)
    t = df["time"].to_numpy()
    dt = pd.to_datetime(df["time"], unit="ms", utc=True)
    anchors = []
    for y, mo, d in zip(dt.dt.year, dt.dt.month, dt.dt.day):
        anchors.append(int(round(pd.Timestamp(year=int(y), month=int(mo), day=int(d), hour=hh, minute=mm, tz=anchor_tz).timestamp() * 1000)))
    out = np.zeros(n)
    pv = vv = 0.0
    for i in range(n):
        new = t[i] >= anchors[i] and (i == 0 or t[i - 1] < anchors[i])
        if new or i == 0:
            pv = vv = 0.0
        pv += src[i] * v[i]
        vv += v[i]
        out[i] = pv / vv if vv else np.nan
    return out


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    tick = 0.01
    sw = max(p["swing"], 2) if p["auto"] else p["swing"]
    s21, s84, s252 = np_sma(c, 21), np_sma(c, 84), np_sma(c, p["s252"])
    d21, d84, d252 = (np.r_[np.nan, x[1:] - x[:-1]] for x in (s21, s84, s252))
    with np.errstate(invalid="ignore"):
        u21, u84, u252 = d21 > 0, d84 > 0, d252 > 0
        w21, w84, w252 = d21 < 0, d84 < 0, d252 < 0
        above = (c > s21) & (c > s84) & (c > s252)
        below = (c < s21) & (c < s84) & (c < s252)
        stack_b, stack_s = (s21 > s84) & (s84 > s252), (s21 < s84) & (s84 < s252)
        dv_b, dv_s = (d21 > d84) & (d84 > d252), (d21 < d84) & (d84 < d252)
    m = p["mode"]
    if m == "All 3 SMAs":
        lso, sso = u21 & u84 & u252, w21 & w84 & w252
    elif m == "2 of 3 SMAs":
        lso, sso = (u21.astype(int) + u84 + u252) >= 2, (w21.astype(int) + w84 + w252) >= 2
    elif m == "SMA 21 Only":
        lso, sso = u21, w21
    else:
        lso, sso = above, below
    lto = lso & (stack_b if p["stack"] else True) & (dv_b if p["diverge"] else True)
    sto = sso & (stack_s if p["stack"] else True) & (dv_s if p["diverge"] else True)
    o4 = (o + h + l + c) / 4
    nyv = vwap_series(df, o4, v, "America/Denver", 7, 30)
    dyv = vwap_series(df, o4, v, "America/Denver", 16, 0)
    dtt = pd.to_datetime(df["time"], unit="ms", utc=True)
    tws, twe = [], []
    for y, mo, d in zip(dtt.dt.year, dtt.dt.month, dtt.dt.day):
        tws.append(int(round(pd.Timestamp(year=int(y), month=int(mo), day=int(d), hour=p["tw"][0], minute=p["tw"][1], tz=p["twtz"]).timestamp() * 1000)))
        twe.append(int(round(pd.Timestamp(year=int(y), month=int(mo), day=int(d), hour=p["tw"][2], minute=p["tw"][3], tz=p["twtz"]).timestamp() * 1000)))
    tms = df["time"].to_numpy()
    inwin = np.ones(n, bool) if not p["usewin"] else np.array([((tms[i] >= tws[i]) or (tms[i] < twe[i])) if twe[i] <= tws[i] else (tms[i] >= tws[i] and tms[i] < twe[i]) for i in range(n)])
    with np.errstate(invalid="ignore"):
        vlo = (~np.isnan(nyv) & (c > nyv) if p["fny"] else np.ones(n, bool)) & (~np.isnan(dyv) & (c > dyv) if p["fdy"] else np.ones(n, bool))
        vso = (~np.isnan(nyv) & (c < nyv) if p["fny"] else np.ones(n, bool)) & (~np.isnan(dyv) & (c < dyv) if p["fdy"] else np.ones(n, bool))
    ph, pl = pivots(h, sw, True), pivots(l, sw, False)
    day = pd.to_datetime(df["time"], unit="ms", utc=True).dt.date.to_numpy()
    body = np.abs(c - o)
    wick = np.fmax((h - l) - body, 0.0)
    sbull = (c > o) & (body >= wick * (1 + p["bow"] / 100))
    sbear = (c < o) & (body >= wick * (1 + p["bow"] / 100))
    bos_only, ch_only = p["bos"], p["choch"]
    use_bos, use_ch = bos_only and not ch_only, ch_only and not bos_only
    etype = lambda is_bos: is_bos if use_bos else ((not is_bos) if use_ch else True)
    S = dict(phv=np.nan, plv=np.nan, ha=False, la=False, bd=0, lsl=np.nan, ltp=np.nan, ssl=np.nan, stp=np.nan, td=0, llp=np.nan, slp=np.nan, lps=0.0)
    nn = lambda x: None if np.isnan(x) else x

    def orders(i, pos, info):
        out = []
        if i > 0 and day[i] != day[i - 1]:
            S["td"] = 0
            if p["eod"]:
                if pos > 0:
                    out.append(("close", "Long"))
                if pos < 0:
                    out.append(("close", "Short"))
            if pos == 0:
                out.append(("cancel_all",))
                S.update(lsl=np.nan, ltp=np.nan, ssl=np.nan, stp=np.nan)
            S["llp"] = S["slp"] = np.nan
            if p["rst"]:
                S.update(phv=np.nan, plv=np.nan, ha=False, la=False, bd=0)
        if ph[i]:
            S["phv"], S["ha"] = h[i - sw], True
        if pl[i]:
            S["plv"], S["la"] = l[i - sw], True
        pH, pL = S["phv"], S["plv"]
        cantr = p["maxd"] == 0 or S["td"] < p["maxd"]
        with np.errstate(invalid="ignore"):
            if p["tick"]:
                bull = S["bd"] != -1
                pok = np.isnan(S["llp"]) or np.isnan(pH) or abs(pH - S["llp"]) > tick
                lok = (p["dir"] != "Short Only" and S["ha"] and not np.isnan(pH) and lto[i] and etype(bull) and vlo[i] and pos <= 0 and cantr and pok
                       and (not np.isnan(pH) and not np.isnan(pL) and pH > pL) and (not np.isnan(pH) and pH > h[i]) and inwin[i])
                if lok:
                    swsl = pH - (pH - pL) * p["swp"] / 100 if p["swon"] else pL
                    base = swsl if p["sl"] == "swing" else (l[i] if p["sl"] == "candle" else pH * (1 - p["slp"] / 100))
                    slc = base - p["bufp"] - pH * p["bufpct"] / 100
                    risk = pH - slc
                    tpc = pH + risk * (p["rrl"] if p["sep"] else p["rr"])
                    if risk > 0 and slc < pH and tpc > pH and slc < tpc:
                        S["lsl"] = slc
                        S["ltp"] = tpc
                        S["llp"] = pH
                        out.append(("entry", "Long", 1, pH, None))
                    else:
                        out.append(("cancel", "Long"))
                else:
                    out.append(("cancel", "Long"))
                bear = S["bd"] != 1
                pok = np.isnan(S["slp"]) or np.isnan(pL) or abs(pL - S["slp"]) > tick
                sok = (p["dir"] != "Long Only" and S["la"] and not np.isnan(pL) and sto[i] and etype(bear) and vso[i] and pos >= 0 and cantr and pok
                       and (not np.isnan(pH) and not np.isnan(pL) and pL < pH) and (not np.isnan(pL) and pL < l[i]) and inwin[i])
                if sok:
                    swsl = pL + (pH - pL) * p["swp"] / 100 if p["swon"] else pH
                    base = swsl if p["sl"] == "swing" else (h[i] if p["sl"] == "candle" else pL * (1 + p["slp"] / 100))
                    slc = base + p["bufp"] + pL * p["bufpct"] / 100
                    risk = slc - pL
                    tpc = pL - risk * (p["rrs"] if p["sep"] else p["rr"])
                    if risk > 0 and slc > pL and tpc < pL and slc > tpc:
                        S["ssl"] = slc
                        S["stp"] = tpc
                        S["slp"] = pL
                        out.append(("entry", "Short", -1, pL, None))
                    else:
                        out.append(("cancel", "Short"))
                else:
                    out.append(("cancel", "Short"))
                if S["ha"] and not np.isnan(pH) and h[i] >= pH:
                    S["ha"], S["bd"] = False, 1
                if S["la"] and not np.isnan(pL) and l[i] <= pL:
                    S["la"], S["bd"] = False, -1
            else:
                if S["ha"] and not np.isnan(pH) and c[i] > pH:
                    S["ha"] = False
                    isb = S["bd"] != -1
                    swsl = c[i] - (c[i] - pL) * p["swp"] / 100 if p["swon"] else pL
                    base = swsl if p["sl"] == "swing" else (l[i] if p["sl"] == "candle" else c[i] * (1 - p["slp"] / 100))
                    slx = base - p["bufp"] - c[i] * p["bufpct"] / 100
                    cok = (not p["strong"]) or sbull[i]
                    pok = np.isnan(S["llp"]) or abs(pH - S["llp"]) > tick
                    stok = not np.isnan(pH) and not np.isnan(pL) and pH > pL
                    if p["dir"] != "Short Only" and etype(isb) and cok and not np.isnan(slx) and lto[i] and vlo[i] and cantr and pok and stok and inwin[i]:
                        risk = c[i] - slx
                        tpc = c[i] + risk * (p["rrl"] if p["sep"] else p["rr"])
                        if risk > 0 and slx < c[i] and tpc > c[i] and slx < tpc and pos <= 0:
                            S["lsl"] = slx
                            S["ltp"] = tpc
                            S["llp"] = pH
                            out.append(("entry", "Long", 1, None, None))
                    S["bd"] = 1
                if S["la"] and not np.isnan(pL) and c[i] < pL:
                    S["la"] = False
                    isb = S["bd"] != 1
                    swsl = c[i] + (pH - c[i]) * p["swp"] / 100 if p["swon"] else pH
                    base = swsl if p["sl"] == "swing" else (h[i] if p["sl"] == "candle" else c[i] * (1 + p["slp"] / 100))
                    slx = base + p["bufp"] + c[i] * p["bufpct"] / 100
                    cok = (not p["strong"]) or sbear[i]
                    pok = np.isnan(S["slp"]) or abs(pL - S["slp"]) > tick
                    stok = not np.isnan(pH) and not np.isnan(pL) and pL < pH
                    if p["dir"] != "Long Only" and etype(isb) and cok and not np.isnan(slx) and sto[i] and vso[i] and cantr and pok and stok and inwin[i]:
                        risk = slx - c[i]
                        tpc = c[i] - risk * (p["rrs"] if p["sep"] else p["rr"])
                        if risk > 0 and slx > c[i] and tpc < c[i] and slx > tpc and pos >= 0:
                            S["ssl"] = slx
                            S["stp"] = tpc
                            S["slp"] = pL
                            out.append(("entry", "Short", -1, None, None))
                    S["bd"] = -1
        if pos > 0 and not np.isnan(S["lsl"]) and not np.isnan(S["ltp"]):
            avg = info["ep"]
            if S["lsl"] < S["ltp"] and S["lsl"] < avg and S["ltp"] > avg:
                out.append(("exit", "Long Exit", "Long", nn(S["lsl"]), nn(S["ltp"])))
            else:
                out.append(("close", "Long"))
        if pos < 0 and not np.isnan(S["ssl"]) and not np.isnan(S["stp"]):
            avg = info["ep"]
            if S["ssl"] > S["stp"] and S["ssl"] > avg and S["stp"] < avg:
                out.append(("exit", "Short Exit", "Short", nn(S["ssl"]), nn(S["stp"])))
            else:
                out.append(("close", "Short"))
        if pos != 0 and S["lps"] == 0:
            S["td"] += 1
        S["lps"] = float(pos)
        return out

    ref = simulate_ord(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, tf="60", params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(swing=1, auto=True, tick=True, bos=True, choch=False, strong=True, bow=100.0, mode="2 of 3 SMAs", stack=False, diverge=True, s252=150, swon=True, swp=80.0, dir="Both", usewin=False, tw=(7, 30, 14, 0), twtz="America/Denver", sl="swing", slp=0.5, bufp=0.0, bufpct=0.0,
            sep=False, rr=0.5, rrl=1.5, rrs=1.5, maxd=0, eod=False, rst=False, fny=False, fdy=False)


def check():
    df = bars(6000, seed=311, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Enter On Tick (BOS candle)": False, "Body > Wick By (%)": 20.0, "Stop Loss Type": "Entry Candle", "SL Buffer (points)": 0.05, "R:R Multiplier (both)": 1.0, "Use SMA Slope Divergence Filter": False},
              dict(tick=False, bow=20.0, sl="candle", bufp=0.05, rr=1.0, diverge=False)),
             ({"Stop Loss Type": "Percent", "Stop Loss %": 0.3, "Enter On BOS Only": False, "Enter On CHoCH Only": True, "Separate Long/Short R:R": True, "Long R:R Multiplier": 1.2,
               "Short R:R Multiplier": 2.0, "SMA Filter Mode": "SMA 21 Only", "Max Trades Per Day (0=unlimited)": 1, "Close Positions at End of Day": True,
               "Reset Structure on New Day": True, "Auto-adjust Pivot Lookback for TF": False, "Use SMA Slope Divergence Filter": False, "Trade Direction": "Long Only"},
              dict(sl="pct", slp=0.3, bos=False, choch=True, sep=True, rrl=1.2, rrs=2.0, mode="SMA 21 Only", maxd=1, eod=True, rst=True, auto=False, diverge=False, dir="Long Only")),
             ({"Filter by NY VWAP": True, "Filter by Daily VWAP": True, "SMA Filter Mode": "Price vs SMA", "Use SMA Slope Divergence Filter": False, "Filter by Trading Window": True,
               "Previous Swing %": "50%"},
              dict(fny=True, fdy=True, mode="Price vs SMA", diverge=False, usewin=True, swp=50.0)),
             ({"SMA Filter Mode": "All 3 SMAs", "Use SMA Stacking Filter": True, "SL Buffer %": 0.05, "Enter On BOS Only": False, "Use % of Previous Swing Distance": False,
               "Trade Direction": "Short Only", "Trading Window Timezone": "UTC", "Filter by Trading Window": True, "Start Hour": 20, "End Hour": 6, "Auto-adjust Pivot Lookback for TF": False},
              dict(mode="All 3 SMAs", stack=True, bufpct=0.05, bos=False, swon=False, dir="Short Only", usewin=True, tw=(20, 30, 6, 0), twtz="UTC", auto=False)))
    for params, ov in cases:
        ok, mm = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(mm)
    return allok, " | ".join(msgs)
