"""Independent check — VWAP Bounce PRO (DvcNmaf7): 15-minute bars (24h synthetic), New York clock, process_orders_on_close, one trade at a time. Daily VWAP (hlc3 x volume) resets at each NY calendar date, weekly VWAP at the first bar of each Monday (and the first bar), session VWAP at the first bar of each 09:30-16:00 session.
Long: Mon-Fri, session bar before 15:00, close above the weekly VWAP, previous low <= previous daily (or session) VWAP and close above the current one (both values must exist); short mirrored (previous high, close below, weekly VWAP). Short loses to long on a tie. At most 2 signals a day (counter reset at the first bar of each NY date), 5 bars between signals,
no new signal while the previous trade is still open (flag cleared at the first script run that finds the position flat). Stop = max(low - 0.3 ATR14, close - 25), target = close + 2 x risk (shorts mirrored; MaxLoss 100 / (2 contracts x 2) = 25 points), bracket works from the next bar. The first bar after the session closes everything at its close. Slippage / commission off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "DvcNmaf7"


def one(df, params, max_loss, cutoff):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    atr = np_atr(h, l, c, 14)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    key = (ny.dt.year * 10000 + ny.dt.month * 100 + ny.dt.day).to_numpy()
    dow = ny.dt.dayofweek.to_numpy()                   # Monday = 0
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    hhmm = (ny.dt.hour * 100 + ny.dt.minute).to_numpy()
    sess = (m >= 570) & (m < 960)
    tp = (h + l + c) / 3.0
    S = dict(dn=0.0, dd=0.0, wn=0.0, wd=0.0, nn=0.0, nd=0.0, tc=0, active=False, last=-1000)
    dv = np.full(n, np.nan)
    nv = np.full(n, np.nan)
    lev = {}
    maxstop = max_loss / (2 * 2.0)

    def orders(i, pos):
        out = []
        new_day = i == 0 or key[i] != key[i - 1]
        new_week = i == 0 or (new_day and dow[i] == 0)
        if new_day:
            S["dn"] = S["dd"] = 0.0
        S["dn"] += tp[i] * v[i]
        S["dd"] += v[i]
        d_v = S["dn"] / S["dd"] if S["dd"] != 0 else np.nan
        if new_week:
            S["wn"] = S["wd"] = 0.0
        S["wn"] += tp[i] * v[i]
        S["wd"] += v[i]
        w_v = S["wn"] / S["wd"] if S["wd"] != 0 else np.nan
        prev_sess = sess[i - 1] if i else False
        if sess[i] and (i == 0 or not prev_sess):
            S["nn"] = S["nd"] = 0.0
        if sess[i]:
            S["nn"] += tp[i] * v[i]
            S["nd"] += v[i]
        n_v = S["nn"] / S["nd"] if (sess[i] and S["nd"] != 0) else np.nan
        dv[i], nv[i] = d_v, n_v
        weekday = dow[i] < 5
        before = hhmm[i] < cutoff

        def bl(vv, v1):
            return (not np.isnan(vv)) and (not np.isnan(v1)) and l[i - 1] <= v1 and c[i] > vv

        def bs(vv, v1):
            return (not np.isnan(vv)) and (not np.isnan(v1)) and h[i - 1] >= v1 and c[i] < vv

        d1 = dv[i - 1] if i else np.nan
        n1 = nv[i - 1] if i else np.nan
        raw_l = sess[i] and (c[i] > w_v) and weekday and before and (bl(d_v, d1) or bl(n_v, n1))
        raw_s = sess[i] and (c[i] < w_v) and weekday and before and (bs(d_v, d1) or bs(n_v, n1))
        if new_day:
            S["tc"] = 0
        under = S["tc"] < 2
        if S["active"] and pos == 0:
            S["active"] = False
        can = (not S["active"]) and (i - S["last"] >= 5) and under
        ls = raw_l and can
        ss = raw_s and can and not ls
        if ls or ss:
            S["active"], S["last"] = True, i
            S["tc"] += 1
        if ls:
            sl = max(l[i] - atr[i] * 0.3, c[i] - maxstop)
            out.append(("entry", 1))
            lev[i] = (sl, c[i] + (c[i] - sl) * 2.0)
        if ss:
            sl = min(h[i] + atr[i] * 0.3, c[i] + maxstop)
            out.append(("entry", -1))
            lev[i] = (sl, c[i] - (sl - c[i]) * 2.0)
        if (not sess[i]) and prev_sess and pos != 0:
            out.append(("close", pos))
        return out

    stop = lambda i, pos, ep, eb: lev[eb][0] if (eb in lev and eb < i) else None
    tgt = lambda i, pos, ep, eb: lev[eb][1] if (eb in lev and eb < i) else None
    with np.errstate(invalid="ignore", divide="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                   strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "commission_value": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(40000, seed=701, freq="15min")
    msgs, allok = [], True
    for params, ml, co in (({}, 100.0, 1500), ({"Max Loss Per Trade ($)": 10.0, "No New Trades After (ET, 24h HHMM)": 1130}, 10.0, 1130)):
        ok, m = one(df, params, ml, co)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
