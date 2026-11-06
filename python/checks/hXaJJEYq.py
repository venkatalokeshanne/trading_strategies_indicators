"""Independent check — El Jaguar SFP FVG Sweep (hXaJJEYq): 5-minute bars (24 h synthetic, price ~4000) on a US stock chart (trading day from 09:30 New York), 1 contract, market orders at the next open, margin / commission / slippage off. Swing high / low = the 1-hour pivots (left-strict, lookback 3) read with lookahead off (a period's value shows on its last chart bar, the previous period's before); a swing-failure pattern = a wick of at least the minimum points through the latest swing that closes back inside; a fair-value gap (low > high[2] by the minimum size with a bullish middle candle; mirrored) inside the SFP window is stored and a retrace into it inside the 09:30-11:30 ET session, with the day's extreme not yet beyond the previous day's, enters at the next open (max trades a day) with the stop beyond the sweep and an R:R target capped by the previous day's extreme; a time stop closes from the chosen ET hour. Uses the pending-order reference broker (simulate_ord).
Variants: defaults; longs only with a wider wick/FVG and one trade a day; shorts only with a 3-point buffer, R:R 3 and the time stop at 13."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_periods, np_security_lookahead_off, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "hXaJJEYq"


def pivots_at_confirmation(x, ln, high):
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
    tick = sym.mintick
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    et = (ny.dt.hour * 100 + ny.dt.minute).to_numpy()
    eth = ny.dt.hour.to_numpy()
    day = (ny.dt.tz_localize(None) - pd.Timedelta(minutes=570)).dt.date.to_numpy()
    pid, last_of = np_periods(df, 60)
    first_of = np.r_[True, pid[1:] != pid[:-1]]
    hh = pd.Series(h).groupby(pid).max().to_numpy()
    ll = pd.Series(l).groupby(pid).min().to_numpy()
    sh_ = np_security_lookahead_off(pivots_at_confirmation(hh, p["swl"], True), pid, last_of)
    sl_ = np_security_lookahead_off(pivots_at_confirmation(ll, p["swl"], False), pid, last_of)
    S = dict(pdh=np.nan, pdl=np.nan, th=np.nan, tl=np.nan, lsh=np.nan, lsl=np.nan, bs=False, ss=False, swl_=np.nan, swh_=np.nan, bsb=None, ssb=None,
             bf=None, brf=None, td=0)

    def orders(i, pos):
        out = []
        nd = i == 0 or day[i] != day[i - 1]
        if nd:
            S["pdh"], S["pdl"], S["th"], S["tl"] = S["th"], S["tl"], h[i], l[i]
        else:
            S["th"], S["tl"] = max(S["th"], h[i]), min(S["tl"], l[i])
        if not np.isnan(sh_[i]):
            S["lsh"] = sh_[i]
        if not np.isnan(sl_[i]):
            S["lsl"] = sl_[i]
        if nd:
            S.update(bs=False, ss=False, swl_=np.nan, swh_=np.nan, bsb=None, ssb=None)
        if not np.isnan(S["lsl"]) and not S["bs"]:
            if l[i] < S["lsl"] - tick and c[i] > S["lsl"] and S["lsl"] - l[i] >= p["wick"]:
                S.update(bs=True, swl_=l[i], bsb=i)
        if not np.isnan(S["lsh"]) and not S["ss"]:
            if h[i] > S["lsh"] + tick and c[i] < S["lsh"] and h[i] - S["lsh"] >= p["wick"]:
                S.update(ss=True, swh_=h[i], ssb=i)
        bv = S["bs"] and S["bsb"] is not None and i - S["bsb"] <= p["sfpage"]
        sv = S["ss"] and S["ssb"] is not None and i - S["ssb"] <= p["sfpage"]
        h2, l2 = (h[i - 2], l[i - 2]) if i >= 2 else (np.nan, np.nan)
        c1, o1 = (c[i - 1], o[i - 1]) if i >= 1 else (np.nan, np.nan)
        with np.errstate(invalid="ignore"):
            bsz = l[i] - h2
            bfv = bsz >= p["fvg"] and c1 > o1
            esz = l2 - h[i]
            efv = esz >= p["fvg"] and c1 < o1
            if bfv and bsz > 0 and bv:
                S["bf"] = (l[i], h2, i)
            if efv and esz > 0 and sv:
                S["brf"] = (l2, h[i], i)
            bfr = S["bf"] is not None and i - S["bf"][2] <= p["fvgage"]
            brfr = S["brf"] is not None and i - S["brf"][2] <= p["fvgage"]
            bret = bfr and l[i] <= S["bf"][0] and c[i] > S["bf"][1]
            sret = brfr and h[i] >= S["brf"][1] and c[i] < S["brf"][0]
            nhp = not np.isnan(S["pdh"]) and S["th"] < S["pdh"]
            nlp = not np.isnan(S["pdl"]) and S["tl"] > S["pdl"]
        if nd:
            S["td"] = 0
        sess = et[i] >= 930 and et[i] < 1130
        can = S["td"] < p["maxt"] and sess and pos == 0
        ls = can and p["longs"] and bv and bret and nhp
        ss = can and p["shorts"] and sv and sret and nlp
        if ls:
            stop = S["swl_"] - p["buf"]
            tp = c[i] + (c[i] - stop) * p["rr"]
            if not np.isnan(S["pdh"]) and S["pdh"] < tp:
                tp = S["pdh"]
            S["td"] += 1
            out += [("entry", "Long", 1, None, None), ("exit", "LX", "Long", stop, tp)]
            S.update(bs=False, bsb=None)
            S["bf"] = None
        if ss:
            stop = S["swh_"] + p["buf"]
            tp = c[i] - (stop - c[i]) * p["rr"]
            if not np.isnan(S["pdl"]) and S["pdl"] > tp:
                tp = S["pdl"]
            S["td"] += 1
            out += [("entry", "Short", -1, None, None), ("exit", "SX", "Short", stop, tp)]
            S.update(ss=False, ssb=None)
            S["brf"] = None
        if pos != 0 and eth[i] >= p["tstop"]:
            out.append(("close_all",))
        return out

    ref = simulate_ord(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(swl=3, wick=1.0, sfpage=30, fvg=1.5, fvgage=20, buf=2.0, rr=2.0, maxt=2, tstop=12, longs=True, shorts=True)


def check():
    df = bars(40000, seed=2468, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 4000 * (df[k] / 100) ** 0.1
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Trade Direction": "Long Only", "Min SFP Wick Points": 3.0, "Min FVG Size (pts)": 0.5, "Max Trades/Day": 1}, dict(shorts=False, wick=3.0, fvg=0.5, maxt=1)),
             ({"Trade Direction": "Short Only", "SL Buffer Beyond Sweep (pts)": 3.0, "Risk:Reward Ratio": 3.0, "Time Stop Hour ET": 13, "Swing Lookback Bars (1H)": 2},
              dict(longs=False, shorts=True, buf=3.0, rr=3.0, tstop=13, swl=2)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
