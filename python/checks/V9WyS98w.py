"""Independent check — Strategy_501 (V9WyS98w): 5-minute bars (24 h synthetic, compressed) on a New York clock, pending stop entries with attached exits. The 06:00-08:59 NY bars give the day's range (state reset when the NY day of the month changes); after it ends the post-range high / low keep extending while flat and untraded. From 09:00 to 12:30 NY a bar whose low is below the range low arms the LONG (cancels the short side), a bar whose high is above the range high arms the SHORT: buy-stop at the post-range high, stop = post-range low - 2, target = entry + risk; the short is the mirror. The orders are renewed on every bar (levels recomputed while flat); after 12:30 unfilled orders are cancelled and the day's state reset; once a position exists the day is "traded"; from 16:00 NY the open position's stop moves to its entry price (the exit is re-issued once). Uses the pending-order reference broker (simulate_ord). Margin off on the pinelib side.
Variants: defaults; a 1.0 stop buffer with a 12:00 window end."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "V9WyS98w"


def one(df, params, buf, endm):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    dom = ny.dt.day.to_numpy()
    inr = (m >= 360) & (m < 540)
    S = dict(taken=False, be=False, rh=np.nan, rl=np.nan, rdy=False, ph=np.nan, pl=np.nan, lowt=False, hit=False, lv=False, sv=False,
             le=np.nan, lsl=np.nan, ltp=np.nan, se=np.nan, ssl=np.nan, stp=np.nan)
    nan = np.nan

    def orders(i, pos, info):
        out = []
        allowed = 540 <= m[i] <= endm
        after_end = m[i] > endm
        be_time = m[i] >= 960
        newday = i == 0 or dom[i] != dom[i - 1]
        if newday:
            S.update(taken=False, be=False)
        newrange = inr[i] and not (i > 0 and inr[i - 1])
        endrange = (not inr[i]) and i > 0 and inr[i - 1]
        if newday:
            S.update(rh=nan, rl=nan, rdy=False, ph=nan, pl=nan)
        if newrange:
            S["rh"], S["rl"] = h[i], l[i]
        if inr[i]:
            S["rh"], S["rl"] = max(S["rh"], h[i]), min(S["rl"], l[i])
        if endrange:
            S["rdy"] = True
            S["ph"], S["pl"] = h[i], l[i]
        if S["rdy"] and not inr[i] and not S["taken"] and pos == 0:
            S["ph"] = h[i] if np.isnan(S["ph"]) else max(S["ph"], h[i])
            S["pl"] = l[i] if np.isnan(S["pl"]) else min(S["pl"], l[i])
        bts = i > 0 and l[i] < l[i - 1] and c[i] > l[i - 1] and c[i] > o[i]
        sts = i > 0 and h[i] > h[i - 1] and c[i] < h[i - 1] and c[i] < o[i]
        if newday:
            S.update(lv=False, sv=False, le=nan, lsl=nan, ltp=nan, se=nan, ssl=nan, stp=nan)
        base = allowed and not S["taken"] and pos == 0
        with np.errstate(invalid="ignore"):
            if S["rdy"] and base and l[i] < S["rl"]:
                S.update(lv=True, sv=False, se=nan, ssl=nan, stp=nan)
                out.append(("cancel", "SHORT"))
            if S["rdy"] and base and h[i] > S["rh"]:
                S.update(sv=True, lv=False, le=nan, lsl=nan, ltp=nan)
                out.append(("cancel", "LONG"))
        have = not np.isnan(S["ph"]) and not np.isnan(S["pl"])
        if S["lv"] and base and have:
            te, ts = S["ph"], S["pl"] - buf
            if te - ts > 0:
                S.update(le=te, lsl=ts, ltp=te + (te - ts))
        if S["sv"] and base and have:
            te, ts = S["pl"], S["ph"] + buf
            if ts - te > 0:
                S.update(se=te, ssl=ts, stp=te - (ts - te))
        if S["lv"] and base and not np.isnan(S["le"]):
            out += [("entry", "LONG", 1, S["le"], None), ("exit", "LONG EXIT", "LONG", S["lsl"], S["ltp"])]
        if S["sv"] and base and not np.isnan(S["se"]):
            out += [("entry", "SHORT", -1, S["se"], None), ("exit", "SHORT EXIT", "SHORT", S["ssl"], S["stp"])]
        if after_end and pos == 0 and not S["taken"]:
            out += [("cancel", "LONG"), ("cancel", "SHORT")]
            S.update(lv=False, sv=False)
        if pos != 0 and not S["taken"]:
            S["taken"] = True
        if be_time and pos > 0 and not S["be"]:
            out.append(("exit", "LONG EXIT", "LONG", info["ep"], S["ltp"]))
            S["be"] = True
        if be_time and pos < 0 and not S["be"]:
            out.append(("exit", "SHORT EXIT", "SHORT", info["ep"], S["stp"]))
            S["be"] = True
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate_ord(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(40000, seed=1212, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.25
    msgs, allok = [], True
    for params, args in (({}, (2.0, 12 * 60 + 30)), ({"SL Buffer": 1.0, "Hora fin entradas": 12, "Minuto fin entradas": 0}, (1.0, 12 * 60))):
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
