"""Independent check — El Pendulo PDH PDL Fade (SsjJP8SK): 5-minute bars (24 h synthetic) on an ES-type future (trading day from 17:00 Chicago for the VWAP), process_orders_on_close, one contract. Regular-session window 09:30-16:00 ET: the previous day's session high / low / midpoint (tracked from the window start and fixed when it ends). In the 21:00-23:55 ET trade window a bar whose high is within 5 of the previous-day high (low within 5 of the low) starts a test (the extreme is tracked); a bearish (bullish) candle with a body >= 2 whose close is within 2 beyond the level arms the signal; within 3 grace bars, before 23:00, under 2 entries per evening (the counter resets on the 20:00 ET bar), flat, with the VWAP on the fade side (close under VWAP for longs, over for shorts), the entry is at the close if the stop distance (extreme -/+ 4) is in (0, 25]; target = the nearer of the midpoint and the 1R level when the midpoint is on the profit side. Exit levels are attached to the entry and work from the next bar. 24 bars after the entry, outside the trade window and at 00:00 ET any open position is closed at the close. Uses the pending-order reference broker (simulate_ord, on_close). Commission / slippage / margin off on the pinelib side.
Variants: defaults; no VWAP filter, risk:reward 1.5 without the midpoint target."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "SsjJP8SK"


def win(n, s, e):
    return (n >= s and n < e) if s <= e else (n >= s or n < e)


def one(df, params, use_vwap, rr, use_mid):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    eh, em = ny.dt.hour.to_numpy(), ny.dt.minute.to_numpy()
    chi = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/Chicago")
    day = (chi.dt.tz_localize(None) - pd.Timedelta(hours=17)).dt.date.to_numpy()
    hl3 = (h + l + c) / 3
    vw = np.zeros(n)
    pv = vv = 0.0
    for i in range(n):
        if i == 0 or day[i] != day[i - 1]:
            pv = vv = 0.0
        pv += hl3[i] * v[i]
        vv += v[i]
        vw[i] = pv / vv
    nan = np.nan
    S = dict(rh=nan, rl=nan, hpd=nan, lpd=nan, mpd=nan, bld=False, td=0, tx=nan, ts=-1, sr=False, sb=-1, sn=0, eb=-1, prth=False)

    def orders(i, pos):
        out = []
        nm = eh[i] * 60 + em[i]
        inrth = win(nm, 570, 960)
        intr = win(nm, 1260, 1435)
        noent = nm >= 1380
        newev = eh[i] == 20 and em[i] == 0 and not (i > 0 and eh[i - 1] == 20 and em[i - 1] == 0)
        rstart = inrth and not S["prth"]
        if rstart:
            if not (np.isnan(S["rh"]) or np.isnan(S["rl"])):
                S["hpd"], S["lpd"], S["mpd"] = S["rh"], S["rl"], (S["rh"] + S["rl"]) / 2
            S["rh"], S["rl"], S["bld"] = h[i], l[i], True
        if inrth and S["bld"]:
            S["rh"] = h[i] if np.isnan(S["rh"]) else max(S["rh"], h[i])
            S["rl"] = l[i] if np.isnan(S["rl"]) else min(S["rl"], l[i])
        rend = (not inrth) and S["prth"] and S["bld"]
        if rend:
            S["hpd"], S["lpd"], S["mpd"], S["bld"] = S["rh"], S["rl"], (S["rh"] + S["rl"]) / 2, False
        S["prth"] = inrth
        ready = not np.isnan(S["hpd"]) and not np.isnan(S["lpd"]) and S["hpd"] > S["lpd"]
        pdh = ready and intr and h[i] >= S["hpd"] - 5.0
        pdl = ready and intr and l[i] <= S["lpd"] + 5.0
        body = abs(c[i] - o[i])
        bull, bear = c[i] > o[i] and body >= 2.0, c[i] < o[i] and body >= 2.0
        if newev:
            S.update(td=0, tx=nan, ts=-1, sr=False, sb=-1)
        if pdh and S["td"] != 1 and not S["sr"]:
            S.update(td=1, tx=h[i], ts=i)
        if pdl and S["td"] != -1 and not S["sr"]:
            S.update(td=-1, tx=l[i], ts=i)
        if S["td"] == 1:
            S["tx"] = h[i] if np.isnan(S["tx"]) else max(S["tx"], h[i])
        if S["td"] == -1:
            S["tx"] = l[i] if np.isnan(S["tx"]) else min(S["tx"], l[i])
        if S["td"] == 1 and not S["sr"] and bear and c[i] <= S["hpd"] + 2.0:
            S["sr"], S["sb"] = True, i
        if S["td"] == -1 and not S["sr"] and bull and c[i] >= S["lpd"] - 2.0:
            S["sr"], S["sb"] = True, i
        if S["td"] != 0 and not S["sr"] and S["ts"] >= 0 and i - S["ts"] > 10:
            S.update(td=0, tx=nan, ts=-1)
        if newev:
            S["sn"] = 0
        flat = pos == 0
        cg = flat and ready and intr and not noent and S["sn"] < 2 and S["sr"]
        grace = S["sb"] >= 0 and S["sb"] <= i <= S["sb"] + grace_bars
        gl = cg and S["td"] == -1 and grace and ((not use_vwap) or c[i] < vw[i])
        gs = cg and S["td"] == 1 and grace and ((not use_vwap) or c[i] > vw[i])
        if gl and not np.isnan(S["tx"]):
            sl = S["tx"] - 4.0
            d = c[i] - sl
            if 0 < d <= 25.0:
                rtp = c[i] + d * rr
                mtp = S["mpd"] if (use_mid and not np.isnan(S["mpd"])) else rtp
                tp = min(mtp, rtp) if (use_mid and mtp > c[i]) else rtp
                if tp <= c[i]:
                    tp = rtp
                out += [("entry", "Long", 1, None, None), ("exit", "LX", "Long", sl, tp)]
                S["sn"] += 1
                S["eb"] = i
                S.update(td=0, tx=nan, ts=-1, sr=False, sb=-1)
        if gs and not np.isnan(S["tx"]):
            sl = S["tx"] + 4.0
            d = sl - c[i]
            if 0 < d <= 25.0:
                rtp = c[i] - d * rr
                mtp = S["mpd"] if (use_mid and not np.isnan(S["mpd"])) else rtp
                tp = max(mtp, rtp) if (use_mid and mtp < c[i]) else rtp
                if tp >= c[i]:
                    tp = rtp
                out += [("entry", "Short", -1, None, None), ("exit", "SX", "Short", sl, tp)]
                S["sn"] += 1
                S["eb"] = i
                S.update(td=0, tx=nan, ts=-1, sr=False, sb=-1)
        if pos != 0 and S["eb"] >= 0 and i - S["eb"] >= 24:
            out.append(("close_all",))
        if pos != 0 and not intr:
            out.append(("close_all",))
        if pos != 0 and eh[i] == 0 and em[i] == 0:
            out.append(("close_all",))
        if S["sr"] and S["sb"] >= 0 and i > S["sb"] + grace_bars and flat:
            S.update(td=0, tx=nan, ts=-1, sr=False, sb=-1)
        return out

    grace_bars = 3
    with np.errstate(invalid="ignore"):
        ref = simulate_ord(o, h, l, c, orders, on_close=True)
    sym = SymbolInfo.make("CME_MINI:ES1!", "futures", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides={"slippage": 0, "commission_value": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(60000, seed=2121, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 5000 * (df[k] / 100) ** 0.1
    msgs, allok = [], True
    cases = (({}, (True, 1.0, True)),
             ({"Use VWAP Directional Filter": False, "R:R Target": 1.5, "Use PDH/PDL Midpoint as TP": False}, (False, 1.5, False)))
    for params, args in cases:
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
