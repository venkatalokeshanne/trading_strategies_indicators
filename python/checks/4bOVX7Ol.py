"""Independent check — Kit Bot v1.1 Silver (4bOVX7Ol): 15-minute bars on a forex-type symbol (trading day from 17:00 New York), one position, market entries at the next open, bracket placed with the entry. Long confirmations (need >= 3): RSI14 in (20, 55) and above RSI of the shifted close (rsiPrev = rsi(close[1])); close back above the lower band while the previous close was <= the CURRENT lower band; close above EMA9;
close above the middle band or (inside the lower half with RSI < 40); hammer or bullish doji; bullish divergence (low lower than the previous low, RSI higher than the previous bar's, previous RSI < 35). Short: RSI > 65 and below rsiPrev; close back below the upper band with the previous close >= the CURRENT upper band; close below EMA9; gravestone or bearish doji;
bearish divergence; RSI crossed below 70. Sessions (GMT bar-start time) London 07:00-16:00 and NYC 13:30-21:00 (Asian off); at most 3 entries per trading day; stop = close -/+ 1.5 ATR, target = 2R (the RR >= 2 test in floating point). Variants: default and 2 confirmations with the Asian session. Margin / slippage off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "4bOVX7Ol"


def one(df, params, minc, asian):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sh = lambda x: np.r_[np.nan, x[:-1]]
    rsi = np_rsi(c, 14)
    rsi_prev = np_rsi(sh(c), 14)
    mid = np_sma(c, 20)
    dev = 2.0 * pd.Series(c).rolling(20, min_periods=20).std(ddof=0).to_numpy()
    up, lo = mid + dev, mid - dev
    ema9, atr = np_ema(c, 9), np_atr(h, l, c, 14)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    day = (ny.dt.tz_localize(None) - pd.Timedelta(hours=17)).dt.date.to_numpy()
    gm = pd.to_datetime(df["time"], unit="ms", utc=True)
    tg = (gm.dt.hour * 100 + gm.dt.minute).to_numpy()
    ins = ((tg >= 700) & (tg < 1600)) | ((tg >= 1330) & (tg < 2100)) | (asian & ((tg >= 2100) | (tg < 130)))
    r1 = sh(rsi)
    with np.errstate(invalid="ignore"):
        body = np.abs(c - o)
        uw, lw = h - np.fmax(c, o), np.fmin(c, o) - l
        grave = (uw > body * 2) & (lw < body * 0.5) & (body > 0)
        hammer = (lw > body * 2) & (uw < body * 0.5) & (body > 0)
        doji = (body < (h - l) * 0.1) & ((h - l) > 0)
        bdiv = (l < sh(l)) & (rsi > r1) & (r1 < 35)
        sdiv = (h > sh(h)) & (rsi < r1) & (r1 > 65)
        pc = sh(c)
        lc = ((rsi < 55) & (rsi > 20) & (rsi > rsi_prev)).astype(int) + ((c > lo) & (pc <= lo)) + (c > ema9) + ((c > mid) | ((c > lo) & (c < mid) & (rsi < 40))) + (hammer | (doji & (c > o))) + bdiv
        sc = ((rsi > 65) & (rsi < rsi_prev)).astype(int) + ((c < up) & (pc >= up)) + (c < ema9) + (grave | (doji & (c < o))) + sdiv + ((r1 > 70) & (rsi < 70))
    S = dict(tt=0)
    lev = {}

    def orders(i, pos):
        out = []
        if i > 0 and day[i] != day[i - 1]:
            S["tt"] = 0
        can = S["tt"] < 3 and ins[i]
        can0 = can
        if pos == 0 and can and lc[i] >= minc:
            ls_, lt_ = c[i] - (atr[i] * 1.5), c[i] + (atr[i] * 1.5 * 2.0)
            if (lt_ - c[i]) / (c[i] - ls_) >= 2.0:
                out.append(("entry", 1))
                lev[i] = (ls_, lt_)
                S["tt"] += 1
        if pos == 0 and can0 and sc[i] >= minc:
            ss_, st_ = c[i] + (atr[i] * 1.5), c[i] - (atr[i] * 1.5 * 2.0)
            if (c[i] - st_) / (ss_ - c[i]) >= 2.0:
                out.append(("entry", -1))
                lev[i] = (ss_, st_)
                S["tt"] += 1
        return out

    stop = lambda i, pos, ep, eb: lev[eb - 1][0] if eb - 1 in lev else None
    tgt = lambda i, pos, ep, eb: lev[eb - 1][1] if eb - 1 in lev else None
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt)
    sym = SymbolInfo.make("OANDA:XAGUSD", "forex", mintick=0.001, qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(40000, seed=871, freq="15min")
    msgs, allok = [], True
    for params, mc, asn in (({}, 3, False), ({"Min Confirmations Required": 2, "Trade Asian Session (21:00-01:30 GMT) !! Caution": True}, 2, True)):
        ok, m = one(df, params, mc, asn)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
