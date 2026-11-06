"""Independent check — 8AM H/L Strategy V2 (lcIPlDAc): 5-minute bars of a 24 h market (UTC) with New York clock times, market orders at the signal close (process_orders_on_close), margin / commission off. The high / low of the New York range window (08:00-09:00 by default) form the day's range (reset at each New York date change); inside the signal window (09:30-11:00) a sweep (wick beyond a level, close back inside) or a tap (within the tick tolerance) arms a setup that must age the confirmation bars (a fresh tap moves its bar) and be followed by a displacement candle (close beyond the previous bar's extreme); at most N signals per side per day and an optional range-percentage filter. Entry at the close with the opposite range extreme as target and the stop at target distance / R:R (skipped when the geometry is wrong); once the high / low covers the trigger percentage of the way to the target the stop is cut to a percentage of its original distance. The exit is issued while the position is open at script time; the stored levels clear the bar after a trade closes. Uses the pending-order reference broker (simulate_ord, on_close).
Variants: defaults (with the 16:00 timed breakeven: a profitable trade's stop goes to the entry, a trade in drawdown is closed once, on the bar whose clock time first reaches it); timed breakeven off; breakeven at 10:30 with R:R 2; 2 confirmation bars, a 5-tick tap tolerance, range filter 50 % and a 1.0 R:R; no stop adjustment, 70 % trigger with 0 % remaining, other windows and max signals 1."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion, simulate_ord

TV_ID = "lcIPlDAc"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    tick = 0.01
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    cm = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    cday = (ny.dt.year * 10000 + ny.dt.month * 100 + ny.dt.day).to_numpy()
    s0, e0 = p["range"][0] * 60 + p["range"][1], p["range"][2] * 60 + p["range"][3]
    g0, g1 = p["sig"][0] * 60 + p["sig"][1], p["sig"][2] * 60 + p["sig"][3]
    S = dict(rh=np.nan, rl=np.nan, bc=0, sc=0, bs=False, ss=False, bsb=None, ssb=None, ae=np.nan, atp=np.nan, asl=np.nan, osl=np.nan, dr=0, adj=False, th=False, pp=None)
    nn = lambda x: None if np.isnan(x) else x

    def orders(i, pos):
        out = []
        pp, S["pp"] = S["pp"], pos
        if i > 0 and cday[i] != cday[i - 1]:
            S.update(rh=np.nan, rl=np.nan, bc=0, sc=0, bs=False, ss=False, bsb=None, ssb=None)
        inr = (cm[i] >= s0 and cm[i] < e0) if s0 < e0 else (cm[i] >= s0 or cm[i] < e0)
        if inr:
            if np.isnan(S["rh"]):
                S["rh"], S["rl"] = h[i], l[i]
            else:
                S["rh"], S["rl"] = max(S["rh"], h[i]), min(S["rl"], l[i])
        sw = cm[i] >= g0 and cm[i] < g1
        ready = not np.isnan(S["rh"]) and not np.isnan(S["rl"])
        rh, rl = S["rh"], S["rl"]
        if ready:
            size = rh - rl
            bfl = rl + size * (p["rpct"] / 100.0)
            sfl = rh - size * (p["rpct"] / 100.0)
        brok = (not p["rfilter"]) or (ready and c[i] <= bfl)
        srok = (not p["rfilter"]) or (ready and c[i] >= sfl)
        tol = p["tol"] * tick
        lsw = ready and sw and l[i] < rl and c[i] > rl
        ltp = ready and sw and l[i] <= rl + tol and l[i] >= rl - tol
        hsw = ready and sw and h[i] > rh and c[i] < rh
        htp = ready and sw and h[i] >= rh - tol and h[i] <= rh + tol
        if S["bc"] < p["maxb"] and (lsw or ltp):
            S["bs"], S["bsb"] = True, i
        if S["sc"] < p["maxs"] and (hsw or htp):
            S["ss"], S["ssb"] = True, i
        if S["bs"] and S["bsb"] is not None and i - S["bsb"] > p["conf"]:
            S["bs"], S["bsb"] = False, None
        if S["ss"] and S["ssb"] is not None and i - S["ssb"] > p["conf"]:
            S["ss"], S["ssb"] = False, None
        bd = c[i] > o[i] and c[i] > (h[i - 1] if i else np.nan)
        sd = c[i] < o[i] and c[i] < (l[i - 1] if i else np.nan)
        bconf = S["bs"] and S["bsb"] is not None and i - S["bsb"] >= p["conf"]
        sconf = S["ss"] and S["ssb"] is not None and i - S["ssb"] >= p["conf"]
        fb = sw and bconf and bd and brok and S["bc"] < p["maxb"]
        fs = sw and sconf and sd and srok and S["sc"] < p["maxs"]
        if fb:
            S["bc"] += 1
            S["bs"], S["bsb"] = False, None
        if fs:
            S["sc"] += 1
            S["ss"], S["ssb"] = False, None
        if fb and pos == 0 and not np.isnan(rh):
            S["ae"], S["atp"] = c[i], rh
            S["asl"] = S["ae"] - (S["atp"] - S["ae"]) / p["rr"]
            S["osl"], S["dr"], S["adj"], S["th"] = abs(S["ae"] - S["asl"]), 1, False, False
            if S["atp"] > S["ae"] and S["asl"] < S["ae"]:
                out += [("entry", "BUY", 1, None, None), ("exit", "BUY EXIT", "BUY", S["asl"], S["atp"])]
        if fs and pos == 0 and not np.isnan(rl):
            S["ae"], S["atp"] = c[i], rl
            S["asl"] = S["ae"] + (S["ae"] - S["atp"]) / p["rr"]
            S["osl"], S["dr"], S["adj"], S["th"] = abs(S["ae"] - S["asl"]), -1, False, False
            if S["atp"] < S["ae"] and S["asl"] > S["ae"]:
                out += [("entry", "SELL", -1, None, None), ("exit", "SELL EXIT", "SELL", S["asl"], S["atp"])]
        inl = pos > 0 and S["dr"] == 1
        ins = pos < 0 and S["dr"] == -1
        with np.errstate(invalid="ignore"):
            if p["adj"] and inl and not S["adj"] and not np.isnan(S["ae"]) and not np.isnan(S["atp"]) and not np.isnan(S["osl"]):
                if h[i] >= S["ae"] + (S["atp"] - S["ae"]) * (p["trig"] / 100.0):
                    S["asl"], S["adj"] = S["ae"] - S["osl"] * (p["rem"] / 100.0), True
            if p["adj"] and ins and not S["adj"] and not np.isnan(S["ae"]) and not np.isnan(S["atp"]) and not np.isnan(S["osl"]):
                if l[i] <= S["ae"] - (S["ae"] - S["atp"]) * (p["trig"] / 100.0):
                    S["asl"], S["adj"] = S["ae"] + S["osl"] * (p["rem"] / 100.0), True
        be = p["be"][0] * 60 + p["be"][1]
        if p["tbe"] and cm[i] >= be and (cm[i - 1] if i else 10**9) < be and not S["th"]:
            if inl and not np.isnan(S["ae"]):
                if c[i] > S["ae"]:
                    S["asl"] = S["ae"]
                elif c[i] < S["ae"]:
                    out.append(("close", "BUY"))
                else:
                    S["asl"] = S["ae"]
                S["th"] = True
            if ins and not np.isnan(S["ae"]):
                if c[i] < S["ae"]:
                    S["asl"] = S["ae"]
                elif c[i] > S["ae"]:
                    out.append(("close", "SELL"))
                else:
                    S["asl"] = S["ae"]
                S["th"] = True
        if inl and not np.isnan(S["atp"]) and not np.isnan(S["asl"]):
            out.append(("exit", "BUY EXIT", "BUY", nn(S["asl"]), nn(S["atp"])))
        if ins and not np.isnan(S["atp"]) and not np.isnan(S["asl"]):
            out.append(("exit", "SELL EXIT", "SELL", nn(S["asl"]), nn(S["atp"])))
        if pos == 0 and pp is not None and pp != 0:
            S.update(ae=np.nan, atp=np.nan, asl=np.nan, osl=np.nan, dr=0, adj=False, th=False)
        return out

    ref = simulate_ord(o, h, l, c, orders, on_close=True)
    ok, d = compare(run_conversion(TV_ID, df, tf="5", params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(range=(8, 0, 9, 0), sig=(9, 30, 11, 0), conf=1, tol=0, maxb=2, maxs=2, rfilter=False, rpct=50.0, rr=0.75, adj=True, trig=80.0, rem=25.0, tbe=True, be=(16, 0))


def check():
    df = bars(30000, seed=606, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.12
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Timed Breakeven": False}, dict(tbe=False)),
             ({"Bar Confirmation": 2, "Tap Tolerance (Ticks)": 5, "Use Range Percentage Filter": True, "Risk : Reward": 1.0},
              dict(conf=2, tol=5, rfilter=True, rr=1.0)),
             ({"Adjust SL After TP Progress": False, "Start Hour": 7, "End Hour": 10, "Signal Start Hour": 10, "Signal Start Minute": 15, "Signal End Hour": 12, "Max Buy Signals": 1, "Max Sell Signals": 1},
              dict(adj=False, range=(7, 0, 10, 0), sig=(10, 15, 12, 0), maxb=1, maxs=1)),
             ({"SL Adjustment Trigger %": 70.0, "SL Remaining %": 0.0, "Risk : Reward": 0.5}, dict(trig=70.0, rem=0.0, rr=0.5)),
             ({"Breakeven Hour": 10, "Breakeven Minute": 30, "Risk : Reward": 2.0, "Adjust SL After TP Progress": False}, dict(be=(10, 30), rr=2.0, adj=False)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
