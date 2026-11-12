"""Independent check — EB ICT One Trade Setup (5IMl4euK; lbMetIvS and Vr9LBPrr are the same script): 15-min continuous bars, "Use EMA 200 Filter" and "Require Rejection Candle" OFF (passed to both sides; they only add boolean gates). Kill zones 07:00-12:00 and 13:00-20:00 New York (bar start). A sweep = low below the latest confirmed
swing low (5 bars each side, strict) with the close back above it (high above the swing high with the close back below for the sell side); it resets the setup, stores the sweep extreme and bar. While alive (<= 40 bars): displacement (candle body > 1.8 x SMA20 of bodies, range > 0.8 ATR14, in the setup direction); FVG after it (low > high[2] / high < low[2]); MSS = close beyond the PREVIOUS value of the
10-bar highest high (lowest low), BOS = beyond the previous 20-bar value once MSS exists - these four windows and their [1] history only advance on bars where the `and` chain reaches them (Pine v6 short-circuit; pinelib's fed-values semantics). Signal: FVG active (<= 25 bars), retest of the gap (low <= top and close > bottom), MSS and BOS found, once per sweep;
entry at the next open, stop = min(sweep level, low) - 0.4 ATR14 (sell: max(.., high) + 0.4 ATR), target 1.5R, fixed on the signal bar."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "5IMl4euK"


def check():
    df = bars(30000, seed=440, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    sess = ((mins >= 420) & (mins < 720)) | ((mins >= 780) & (mins < 1200))
    atr = np_atr(h, l, c, 14)
    avgb = np_sma(np.abs(c - o), 20)
    S = dict(lh=np.nan, ll=np.nan, dir=0, sw=False, disp=False, fvg=False, mss=False, bos=False, traded=False, slv=np.nan, sbar=-10**9,
             ft=np.nan, fb=np.nan, fbar=-10**9)
    feeds = {"hh10": [], "ll10": [], "hh20": [], "ll20": []}
    prevv = {"hh10": np.nan, "ll10": np.nan, "hh20": np.nan, "ll20": np.nan}

    def site(key, src, i, n_, fn):
        feeds[key].append(src[i])
        cur = fn(feeds[key][-n_:]) if len(feeds[key]) >= n_ else np.nan
        p = prevv[key]
        prevv[key] = cur
        return p                               # the call's value on the PREVIOUS execution = [1]

    lvl = {}

    def orders(i, pos):
        out = []
        if i >= 10:
            m = i - 5
            w = h[m - 5:m + 6]
            if h[m] == w.max() and (w == h[m]).sum() == 1:
                S["lh"] = h[m]
            w = l[m - 5:m + 6]
            if l[m] == w.min() and (w == l[m]).sum() == 1:
                S["ll"] = l[m]
        with np.errstate(invalid="ignore"):
            bsw = sess[i] and not np.isnan(S["ll"]) and l[i] < S["ll"] and c[i] > S["ll"]
            ssw = sess[i] and not np.isnan(S["lh"]) and h[i] > S["lh"] and c[i] < S["lh"]
        for d, flag, lvl_ in ((1, bsw, l[i]), (-1, ssw, h[i])):
            if flag:
                S.update(dir=d, sw=True, disp=False, fvg=False, mss=False, bos=False, traded=False, slv=lvl_, sbar=i)
        alive = S["sw"] and i - S["sbar"] <= 40
        body = abs(c[i] - o[i])
        big = (h[i] - l[i]) > atr[i] * 0.8
        with np.errstate(invalid="ignore"):
            bd = alive and S["dir"] == 1 and c[i] > o[i] and body > avgb[i] * 1.8 and big
            sd = alive and S["dir"] == -1 and c[i] < o[i] and body > avgb[i] * 1.8 and big
        if bd or sd:
            S["disp"] = True
        if i >= 2:
            if S["disp"] and S["dir"] == 1 and l[i] > h[i - 2]:
                S.update(ft=l[i], fb=h[i - 2], fbar=i, fvg=True)
            if S["disp"] and S["dir"] == -1 and h[i] < l[i - 2]:
                S.update(ft=l[i - 2], fb=h[i], fbar=i, fvg=True)
        fact = S["fvg"] and i - S["fbar"] <= 25
        bm = sm = False
        if alive and S["dir"] == 1:
            p = site("hh10", h, i, 10, max)
            bm = bool(c[i] > p)
        if alive and S["dir"] == -1:
            p = site("ll10", l, i, 10, min)
            sm = bool(c[i] < p)
        if bm or sm:
            S["mss"] = True
        bb = sb = False
        if alive and S["dir"] == 1 and S["mss"]:
            p = site("hh20", h, i, 20, max)
            bb = bool(c[i] > p)
        if alive and S["dir"] == -1 and S["mss"]:
            p = site("ll20", l, i, 20, min)
            sb = bool(c[i] < p)
        if bb or sb:
            S["bos"] = True
        with np.errstate(invalid="ignore"):
            brt = fact and S["dir"] == 1 and l[i] <= S["ft"] and c[i] > S["fb"]
            srt = fact and S["dir"] == -1 and h[i] >= S["fb"] and c[i] < S["ft"]
        score = (25 if S["sw"] else 0) + (20 if S["disp"] else 0) + (10 if S["fvg"] else 0) + (20 if S["mss"] else 0) + (15 if S["bos"] else 0) + (10 if (brt or srt) else 0)
        buy = score >= 85 and S["dir"] == 1 and brt and S["mss"] and S["bos"]
        sell = score >= 85 and S["dir"] == -1 and srt and S["mss"] and S["bos"]
        with np.errstate(invalid="ignore"):
            bsl = min(S["slv"], l[i]) - atr[i] * 0.4
            ssl = max(S["slv"], h[i]) + atr[i] * 0.4
        brisk, srisk = c[i] - bsl, ssl - c[i]
        if buy and not S["traded"] and brisk > 0.01:
            out.append(("entry", 1))
            lvl[1] = (bsl, c[i] + brisk * 1.5)
            S["traded"] = True
        if sell and not S["traded"] and srisk > 0.01:
            out.append(("entry", -1))
            lvl[-1] = (ssl, c[i] - srisk * 1.5)
            S["traded"] = True
        return out

    def stop(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][0]

    def target(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params={"Use EMA 200 Filter": False, "Require Rejection Candle": False},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
