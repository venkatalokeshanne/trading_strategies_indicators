"""Independent check — MES Scalperino (o0DUiYSC): 15-minute bars of an ES-type future with the weekend and a daily break removed (so gaps between bars occur), market orders at the next open. A signal fires on bar t; the order is placed on bar t+1 (the source reads signal[1]) when the New York hour is in the session window and the position is flat (or reversible), and fills at the open of t+2 with a take-profit of 1.5 points and a stop of 50 points from the fill price, working from the fill bar. The position is closed at the next open when the gap between this bar and the previous exceeds the set minutes, or when the bars since the ORDER bar reach the maximum. Signals: SMA(20) x> SMA(50), EMA(50) x> EMA(100), RSI(9) < 20, RSI(14) < 25 / 20, SMA(50) > SMA(200), EMA(50) > EMA(100), combined options and their short mirrors. Commission off on the pinelib side.
Variants: defaults (long only, SMA cross, evening session); both directions with reversal, EMA state signals, no session filter, max hold 40; short only on RSI(14) > 75 in the full ETH session with a 25-point stop."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "o0DUiYSC"


def cu(a, b):
    pa, pb = np.r_[np.nan, a[:-1]], np.r_[np.nan, b[:-1]]
    with np.errstate(invalid="ignore"):
        return (a > b) & (pa <= pb)


def cd(a, b):
    pa, pb = np.r_[np.nan, a[:-1]], np.r_[np.nan, b[:-1]]
    with np.errstate(invalid="ignore"):
        return (a < b) & (pa >= pb)


def one(df, params, direction, lsig, ssig, rev, sess, maxhold, slp, tpp=1.5):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    t = df["time"].to_numpy()
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    hr = ny.dt.hour.to_numpy()
    sma20, sma50, sma200 = np_sma(c, 20), np_sma(c, 50), np_sma(c, 200)
    ema50, ema100 = np_ema(c, 50), np_ema(c, 100)
    r9, r14 = np_rsi(c, 9), np_rsi(c, 14)
    with np.errstate(invalid="ignore"):
        L = {"sma": cu(sma20, sma50) & ~np.isnan(sma50), "ema": cu(ema50, ema100), "r9": r9 < 20, "r14_25": r14 < 25, "r14_20": r14 < 20,
             "smastate": sma50 > sma200, "emastate": ema50 > ema100}
        Sx = {"sma": cd(sma20, sma50) & ~np.isnan(sma50), "ema": cd(ema50, ema100), "r9": r9 > 80, "r14_25": r14 > 75, "r14_20": r14 > 80,
              "smastate": sma50 < sma200, "emastate": ema50 < ema100}
    lf = L[lsig] if direction in ("long", "both") else np.zeros(n, bool)
    sf = Sx[ssig] if direction in ("short", "both") else np.zeros(n, bool)
    lp, sp = np.r_[False, lf[:-1]], np.r_[False, sf[:-1]]
    allow = {"none": np.ones(n, bool), "evening": (hr >= 18) | (hr < 1), "eth": (hr < 9) | (hr >= 16)}[sess]
    S = dict(eb=None)

    def orders(i, pos):
        out = []
        canrev = direction == "both" and rev
        el = lp[i] and allow[i] and (pos == 0 or (canrev and pos < 0))
        es = sp[i] and allow[i] and (pos == 0 or (canrev and pos > 0))
        if el:
            S["eb"] = i
            out.append(("entry", 1))
        if es:
            S["eb"] = i
            out.append(("entry", -1))
        gap = i > 0 and (t[i] - t[i - 1]) / 60000 > 120
        if pos != 0 and S["eb"] is not None:
            if gap or i - S["eb"] >= maxhold:
                out.append(("close", pos))
        return out

    stop = lambda i, pos, ep, eb: ep - pos * slp
    tgt = lambda i, pos, ep, eb: ep + pos * tpp
    ref = simulate(o, h, l, c, orders, stop=stop, target=tgt)
    sym = SymbolInfo.make("CME_MINI:MES1!", "futures", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides={"commission_value": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(30000, seed=2323, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 5000 * (df[k] / 100) ** 0.1
    t = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    keep = (t.dt.dayofweek < 5) & ~((t.dt.hour == 17))          # weekends and the 17:00 hour removed -> gaps
    df = df[keep.to_numpy()].reset_index(drop=True)
    msgs, allok = [], True
    cases = (({}, ("long", "sma", None, False, "evening", 480, 50.0)),
             ({"Direction": "Both", "Both Signal": "EMA(50)/EMA(100) State", "Allow Reversal": True, "Session Filter": "No Filter", "Max Hold (bars)": 40},
              ("both", "emastate", "emastate", True, "none", 40, 50.0)),
             ({"Direction": "Short Only", "Short Signal": "RSI(14) >75", "Session Filter": "Full ETH (outside RTH)", "Stop Loss (points)": 25.0},
              ("short", None, "r14_25", False, "eth", 480, 25.0)))
    for params, args in cases:
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
