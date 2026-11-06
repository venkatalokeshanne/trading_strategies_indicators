"""Independent check — ORB AVWAP Retest (QK2FNhOB): 5-minute bars (24h synthetic), New York clock, trading day starting 09:30 NY, process_orders_on_close, one position. Per trading day: opening range = high / low of bars starting 09:30-09:44; ready from the first bar >= 09:45 with high > low (stays ready
until the next 09:30, so the bars after midnight still count); cumulative hlc3 x volume anchored at the 09:30 bar (also accumulated from 16:00 to midnight, not after midnight). A close above the range high (below the low) while flat, not yet traded and not after 16:00 sets the breakout direction; a later bar whose low <= AVWAP
and closes above it, bullish, with low above the range low (shorts mirrored) enters at the close: stop = range low (or entry -/+ ATR x mult), target = entry +/- Target R x risk, qty = min(50, floor(800 / risk)) > 0. Bracket works from the next bar. One trade per day. Variants: default, ATR stop with 2R, several trades a day. Margin off on pinelib side."""
import math

import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "QK2FNhOB"


def one(df, params, atr_stop, tr_, one_trade):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    atr = np_atr(h, l, c, 14)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    now = (ny.dt.hour * 10000 + ny.dt.minute * 100).to_numpy()
    day = (ny.dt.tz_localize(None) - pd.Timedelta(minutes=9 * 60 + 30)).dt.date.to_numpy()
    hlc3 = (h + l + c) / 3
    S = dict(rh=np.nan, rl=np.nan, ready=False, bd=0, bb=-1, traded=False, pv=0.0, vol=0.0)
    lev = {}

    def orders(i, pos):
        out = []
        if i > 0 and day[i] != day[i - 1]:
            S.update(rh=np.nan, rl=np.nan, ready=False, bd=0, bb=-1, traded=False, pv=0.0, vol=0.0)
        if now[i] >= 93000:
            S["pv"] += hlc3[i] * v[i]
            S["vol"] += v[i]
        av = S["pv"] / S["vol"] if S["vol"] > 0 else np.nan
        if 93000 <= now[i] < 94500:
            S["rh"] = h[i] if np.isnan(S["rh"]) else max(S["rh"], h[i])
            S["rl"] = l[i] if np.isnan(S["rl"]) else min(S["rl"], l[i])
        if now[i] >= 94500 and not S["ready"] and not np.isnan(S["rh"]) and not np.isnan(S["rl"]) and S["rh"] > S["rl"]:
            S["ready"] = True
        can = S["ready"] and now[i] <= 160000 and ((not one_trade) or (not S["traded"])) and pos == 0
        if can and S["bd"] == 0:
            if c[i] > S["rh"]:
                S["bd"], S["bb"] = 1, i
            elif c[i] < S["rl"]:
                S["bd"], S["bb"] = -1, i
        lrr = S["bd"] == 1 and i > S["bb"] and l[i] <= av and c[i] > av and c[i] > o[i] and l[i] > S["rl"]
        srr = S["bd"] == -1 and i > S["bb"] and h[i] >= av and c[i] < av and c[i] < o[i] and h[i] < S["rh"]
        if can and lrr:
            sp = c[i] - atr[i] * 1.0 if atr_stop else S["rl"]
            risk = c[i] - sp
            q = min(50, math.floor(800 / risk)) if abs(risk) > 0 else 0
            if risk > 0 and q > 0:
                out.append(("entry", 1))
                lev[i] = (sp, c[i] + risk * tr_)
                S["traded"], S["bd"] = True, 0
        if can and srr:
            sp = c[i] + atr[i] * 1.0 if atr_stop else S["rh"]
            risk = sp - c[i]
            q = min(50, math.floor(800 / risk)) if abs(risk) > 0 else 0
            if risk > 0 and q > 0:
                out.append(("entry", -1))
                lev[i] = (sp, c[i] - risk * tr_)
                S["traded"], S["bd"] = True, 0
        return out

    stop = lambda i, pos, ep, eb: lev[eb][0] if (eb in lev and eb < i) else None
    tgt = lambda i, pos, ep, eb: lev[eb][1] if (eb in lev and eb < i) else None
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(40000, seed=661, freq="5min")
    msgs, allok = [], True
    for params, atr_stop, tr_, one_trade in (({}, False, 1.0, True), ({"Stop Mode": "ATR", "Target R": 2.0}, True, 2.0, True), ({"One Trade Per Session": False}, False, 1.0, False)):
        ok, m = one(df, params, atr_stop, tr_, one_trade)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
