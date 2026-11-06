"""Independent check — Turtle Soup NY V4 (qfqRq8DM): 15-minute bars (24h synthetic), New York clock. Range = bars starting 06:00-08:59 of each calendar day (high / low accumulated from the first range bar, reset at the first bar after midnight), usable
from the first bar after the range. Between 09:30 and 12:00 (inclusive of the 12:00 bar) a bar sweeping the range low (high) arms a long (short) setup, remembering that bar's low (high) (a later same-bar sweep of the other side replaces the setup; setups are NOT reset at the day change).
Entry when the setup is armed and the bar closes as a bullish (bearish) rejection (close beyond the midpoint): stop = sweep extreme -/+ 2, target = the range high (low), reward / risk >= 1, not time-gated; one trade a day (flag reset at the first bar of a new NY calendar day). Bracket placed with the entry (works from the fill bar). Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "qfqRq8DM"


def check():
    df = bars(30000, seed=611, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    d = ny.dt.day.to_numpy()
    in_r = (m >= 360) & (m <= 539)
    allowed = (m >= 570) & (m <= 720)
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
        if S["ready"] and allowed[i] and not S["taken"]:
            if l[i] < S["rl"]:
                S["ls"], S["ss"], S["lml"] = True, False, l[i]
        if S["ready"] and allowed[i] and not S["taken"]:
            if h[i] > S["rh"]:
                S["ss"], S["ls"], S["smh"] = True, False, h[i]
        mid = (h[i] + l[i]) / 2
        lsig = ssig = False
        if S["ls"] and c[i] > o[i] and c[i] > mid:
            sl = S["lml"] - 2.0
            risk, reward = c[i] - sl, S["rh"] - c[i]
            if risk != 0 and reward / risk >= 1.0:
                lsig, lsl, ltp = True, sl, S["rh"]
        if S["ss"] and c[i] < o[i] and c[i] < mid:
            sl = S["smh"] + 2.0
            risk, reward = sl - c[i], c[i] - S["rl"]
            if risk != 0 and reward / risk >= 1.0:
                ssig, ssl, stp = True, sl, S["rl"]
        if lsig and pos == 0 and not S["taken"]:
            out.append(("entry", 1))
            lev[i] = (lsl, ltp)
            S["taken"], S["ls"] = True, False
        if ssig and pos == 0 and not S["taken"]:
            out.append(("entry", -1))
            lev[i] = (ssl, stp)
            S["taken"], S["ss"] = True, False
        return out

    stop = lambda i, pos, ep, eb: lev[eb - 1][0] if eb - 1 in lev else None
    tgt = lambda i, pos, ep, eb: lev[eb - 1][1] if eb - 1 in lev else None
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, dd = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{dd} (got {len(ref)})"
