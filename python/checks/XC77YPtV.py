"""Independent check — Turtle Soup NY V5 M5 sweep (XC77YPtV): 5-minute bars (24h synthetic), New York clock, process_orders_on_close, one position. Range = bars starting 06:00-08:59 of each calendar day, usable from the first bar after the range. Between 09:00 and 12:00 (the 12:00 bar included) a bar that trades below (above) the range low (high) arms a long (short) setup and accumulates the lowest low (highest high) of the sweep bars
(the opposite sweep replaces the setup and clears the other extreme; setups are NOT reset at the day change). Entry at the close of the next bar that trades below the previous low, closes back above it and is bullish (mirrored for shorts), while armed, flat and not yet traded that day: stop = min(manipulation low, bar low) - 2 (max(..., bar high) + 2), target = the opposite range side, reward and risk positive and reward / risk >= 1. Bracket placed with the entry. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "XC77YPtV"


def check():
    df = bars(60000, seed=611, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    d = ny.dt.day.to_numpy()
    in_r = (m >= 360) & (m <= 539)
    allowed = (m >= 540) & (m <= 720)
    S = dict(rh=np.nan, rl=np.nan, ready=False, taken=False, ls=False, ss=False, lml=np.nan, smh=np.nan)
    lev = {}

    def orders(i, pos):
        out = []
        new_day = i > 0 and d[i] != d[i - 1]
        if new_day:
            S["taken"] = False
            S["rh"] = S["rl"] = np.nan
            S["ready"] = False
        pin = in_r[i - 1] if i else False
        if in_r[i] and not pin:
            S["rh"], S["rl"] = h[i], l[i]
        if in_r[i]:
            S["rh"], S["rl"] = max(S["rh"], h[i]) if not np.isnan(S["rh"]) else np.nan, min(S["rl"], l[i]) if not np.isnan(S["rl"]) else np.nan
        if (not in_r[i]) and pin:
            S["ready"] = True
        pl_ = l[i - 1] if i else np.nan
        ph_ = h[i - 1] if i else np.nan
        bull5 = l[i] < pl_ and c[i] > pl_ and c[i] > o[i]
        bear5 = h[i] > ph_ and c[i] < ph_ and c[i] < o[i]
        if S["ready"] and allowed[i] and not S["taken"] and l[i] < S["rl"]:
            S["ls"], S["ss"] = True, False
            S["lml"] = l[i] if np.isnan(S["lml"]) else min(S["lml"], l[i])
            S["smh"] = np.nan
        if S["ready"] and allowed[i] and not S["taken"] and h[i] > S["rh"]:
            S["ss"], S["ls"] = True, False
            S["smh"] = h[i] if np.isnan(S["smh"]) else max(S["smh"], h[i])
            S["lml"] = np.nan
        lsig = ssig = False
        if S["ls"] and allowed[i] and not S["taken"] and pos == 0 and bull5:
            sl = min(S["lml"], l[i]) - 2.0
            risk, reward = c[i] - sl, S["rh"] - c[i]
            if risk > 0 and reward > 0 and reward / risk >= 1.0:
                lsig, lsl, ltp = True, sl, S["rh"]
        if S["ss"] and allowed[i] and not S["taken"] and pos == 0 and bear5:
            sl = max(S["smh"], h[i]) + 2.0
            risk, reward = sl - c[i], c[i] - S["rl"]
            if risk > 0 and reward > 0 and reward / risk >= 1.0:
                ssig, ssl, stp = True, sl, S["rl"]
        if lsig and pos == 0 and not S["taken"]:
            out.append(("entry", 1))
            lev[i] = (lsl, ltp)
            S["taken"], S["ls"], S["lml"] = True, False, np.nan
        if ssig and pos == 0 and not S["taken"]:
            out.append(("entry", -1))
            lev[i] = (ssl, stp)
            S["taken"], S["ss"], S["smh"] = True, False, np.nan
        return out

    stop = lambda i, pos, ep, eb: lev[eb][0] if (eb in lev and eb < i) else None
    tgt = lambda i, pos, ep, eb: lev[eb][1] if (eb in lev and eb < i) else None
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, dd = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{dd} (got {len(ref)})"
