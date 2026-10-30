"""Independent check — VWAP Stdev Bands Reversal (X1tap85S): 5-minute bars (24 h synthetic) on a US stock chart (trading day from 09:30 New York), process_orders_on_close for market orders, resting limit entries. VWAP of hl2 x volume reset on the trading day with the volume-weighted standard deviation; bands at +/- 2.51 (extreme) and 2.01 (second) deviations. Arm long when the low reaches the lower extreme band or the close is under the lower second band (short mirrored), outside the first 3 bars of the session and the last 5 (relative to the previous session's length), arms expire after 500 bars and at the session start. A bullish candle closing at or under the VWAP while armed fires the long signal (a bullish candle closing above it cancels the arm); reward:risk to the upper second band over the 5-bar swing stop must be >= 1.5. A signal reverses an open short (market close at this bar's close) and places a limit entry at the signal close that is cancelled when older than 3 bars while not long; once filled (seen at the next script run) its exit (stop = swing low at signal, target = upper second band at signal) is issued, working from the following bar. Uses the pending-order reference broker (simulate_ord, on_close). Margin / commission off on the pinelib side.
Variants: defaults; 2 / 1 bands with minimum RR 1 and a 2-bar limit expiry; market entries (limit off)."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "X1tap85S"


def one(df, params, ext, sec, min_rr, use_limit, lim_exp, mults):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    day = (ny.dt.tz_localize(None) - pd.Timedelta(minutes=570)).dt.date.to_numpy()
    hl2 = (h + l) / 2
    S = dict(vs=0.0, vv=0.0, v2=0.0, bss=0, psl=None, rl=0, am=False, al=False, sa=0, la=0, lage=None, sage=None, lsig=None, ssig=None, ltp=None, stp=None)
    low5 = np.array([l[i - 4:i + 1].min() if i >= 4 else np.nan for i in range(n)])
    high5 = np.array([h[i - 4:i + 1].max() if i >= 4 else np.nan for i in range(n)])

    def orders(i, pos):
        out = []
        ns = i == 0 or day[i] != day[i - 1]
        if ns:
            S["vs"], S["vv"], S["v2"] = hl2[i] * v[i], v[i], v[i] * hl2[i] ** 2
        else:
            S["vs"] += hl2[i] * v[i]
            S["vv"] += v[i]
            S["v2"] += v[i] * hl2[i] ** 2
        vw = S["vs"] / S["vv"]
        dev = np.sqrt(max(S["v2"] / S["vv"] - vw * vw, 0))
        upx, dnx = vw + mults[ext] * dev, vw - mults[ext] * dev
        up2, dn2 = vw + mults[sec] * dev, vw - mults[sec] * dev
        S["bss"] = 0 if ns else S["bss"] + 1
        if ns:
            S["psl"] = S["rl"]
            S["rl"] = 0
        else:
            S["rl"] += 1
        wok = S["bss"] >= 3
        cok = S["psl"] is None or S["bss"] < S["psl"] - 5
        sok = wok and cok
        utr = ((h[i] >= upx) or (c[i] > up2)) and sok
        dtr = ((l[i] <= dnx) or (c[i] < dn2)) and sok
        if ns:
            S.update(am=False, al=False, sa=0, la=0)
        if S["am"]:
            S["sa"] += 1
            if S["sa"] > 500:
                S["am"] = False
        if S["al"]:
            S["la"] += 1
            if S["la"] > 500:
                S["al"] = False
        if utr:
            S["am"], S["sa"] = True, 0
        if dtr:
            S["al"], S["la"] = True, 0
        bull, bear = c[i] > o[i], c[i] < o[i]
        lsg = S["al"] and bull and c[i] <= vw
        ssg = S["am"] and bear and c[i] >= vw
        lcn = S["al"] and bull and c[i] > vw
        scn = S["am"] and bear and c[i] < vw
        if lsg or lcn:
            S["al"] = False
        if ssg or scn:
            S["am"] = False
        ls_, ss_ = low5[i], high5[i]
        lrr = (up2 - c[i]) / (c[i] - ls_) if (c[i] - ls_) > 0 else 0
        srr = (c[i] - dn2) / (ss_ - c[i]) if (ss_ - c[i]) > 0 else 0
        lok = lsg and lrr >= min_rr
        sok_ = ssg and srr >= min_rr
        flat, il, is_ = pos == 0, pos > 0, pos < 0
        el = lok and (flat or is_)
        es = sok_ and (flat or il)
        if el:
            if is_:
                out.append(("close", "Short"))
            if use_limit:
                S["lsig"], S["ltp"], S["lage"] = ls_, up2, 0
                out.append(("entry", "Long", 1, None, c[i]))
            else:
                out += [("entry", "Long", 1, None, None), ("exit", "Long X", "Long", None if np.isnan(ls_) else ls_, up2)]
        if es:
            if il:
                out.append(("close", "Long"))
            if use_limit:
                S["ssig"], S["stp"], S["sage"] = ss_, dn2, 0
                out.append(("entry", "Short", -1, None, c[i]))
            else:
                out += [("entry", "Short", -1, None, None), ("exit", "Short X", "Short", None if np.isnan(ss_) else ss_, dn2)]
        if use_limit:
            if S["lage"] is not None and pos <= 0:
                S["lage"] += 1
                if S["lage"] > lim_exp:
                    out.append(("cancel", "Long"))
                    S["lage"] = None
            if il and S["lsig"] is not None:
                out.append(("exit", "Long X", "Long", None if np.isnan(S["lsig"]) else S["lsig"], S["ltp"]))
                S["lsig"] = None
                S["lage"] = None
            if S["sage"] is not None and pos >= 0:
                S["sage"] += 1
                if S["sage"] > lim_exp:
                    out.append(("cancel", "Short"))
                    S["sage"] = None
            if is_ and S["ssig"] is not None:
                out.append(("exit", "Short X", "Short", None if np.isnan(S["ssig"]) else S["ssig"], S["stp"]))
                S["ssig"] = None
                S["sage"] = None
        return out

    with np.errstate(invalid="ignore", divide="ignore"):
        ref = simulate_ord(o, h, l, c, orders, on_close=True)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(30000, seed=515, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    m1 = {1: 1.28, 2: 2.01, 3: 2.51, 4: 3.09, 5: 4.01}
    cases = (({}, (3, 2, 1.5, True, 3, m1)),
             ({"Most extreme band (1-5)": 2, "Second most extreme band (1-5)": 1, "Minimum Risk:Reward": 1.0, "Limit order expiry (bars)": 2}, (2, 1, 1.0, True, 2, m1)),
             ({"Use resting limit entries (maker)": False, "Minimum Risk:Reward": 1.0}, (3, 2, 1.0, False, 3, m1)))
    for params, args in cases:
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
