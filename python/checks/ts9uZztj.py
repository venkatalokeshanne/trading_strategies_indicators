"""Independent check — Kit Bot v1.2 Silver (ts9uZztj): 15-minute bars on a forex-type symbol (trading day from 17:00 New York), one position, market entries at the next open, bracket placed with the entry. Long gates (all): RSI14 rising and in (18, 50); close above EMA9; the lowest low of the last 5 bars <= the lower Bollinger band. Bonus (>= 2 of 5): close back above the lower band with the previous close <= the CURRENT lower band;
hammer (wick > 2.5 body, other wick < 0.3 body) / bullish engulfing / bullish doji (body < 8 % of the range, longer lower wick); bullish divergence (a confirmed pivot low (3 bars each side) now, with low[3] < low[6] and rsi[3] > rsi[6], rsi[3] < 40); volume > 1.2 x SMA20(volume); close above EMA50. Short mirrored (RSI falling in (55, 82), highest high of the last 5 >= upper band, ...). London / NYC sessions by GMT bar start,
at most 3 entries per trading day, stop = close -/+ 1.5 ATR, target = 2R. Margin / slippage off on the pinelib side. Variants: default and 3 bonus confirmations with the Asian session."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "ts9uZztj"


def one(df, params, minc, asian):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    sh = lambda x: np.r_[np.nan, x[:-1]]
    rsi = np_rsi(c, 14)
    mid = np_sma(c, 20)
    dev = 2.0 * pd.Series(c).rolling(20, min_periods=20).std(ddof=0).to_numpy()
    up, lo = mid + dev, mid - dev
    ema9, ema50, atr = np_ema(c, 9), np_ema(c, 50), np_atr(h, l, c, 14)
    vavg = np_sma(v, 20)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    day = (ny.dt.tz_localize(None) - pd.Timedelta(hours=17)).dt.date.to_numpy()
    gm = pd.to_datetime(df["time"], unit="ms", utc=True)
    tg = (gm.dt.hour * 100 + gm.dt.minute).to_numpy()
    ins = ((tg >= 700) & (tg < 1600)) | ((tg >= 1330) & (tg < 2100)) | (asian & ((tg >= 2100) | (tg < 130)))
    r1, r3, r6 = sh(rsi), np.r_[np.full(3, np.nan), rsi[:-3]], np.r_[np.full(6, np.nan), rsi[:-6]]
    h3, h6, l3, l6 = np.r_[np.full(3, np.nan), h[:-3]], np.r_[np.full(6, np.nan), h[:-6]], np.r_[np.full(3, np.nan), l[:-3]], np.r_[np.full(6, np.nan), l[:-6]]
    ph, pl = np.zeros(n, bool), np.zeros(n, bool)
    for i in range(6, n):
        j = i - 3
        ph[i] = h[j] > h[j - 3:j].max() and h[j] > h[j + 1:i + 1].max()
        pl[i] = l[j] < l[j - 3:j].min() and l[j] < l[j + 1:i + 1].min()
    lo5 = pd.Series(l).rolling(5, min_periods=5).min().to_numpy()
    hi5 = pd.Series(h).rolling(5, min_periods=5).max().to_numpy()
    with np.errstate(invalid="ignore"):
        body = np.abs(c - o)
        uw, lw, rg = h - np.fmax(c, o), np.fmin(c, o) - l, h - l
        grave = (rg > 0) & (uw > body * 2.5) & (lw < body * 0.3) & (body > 0)
        hammer = (rg > 0) & (lw > body * 2.5) & (uw < body * 0.3) & (body > 0)
        doji = (rg > 0) & (body < rg * 0.08)
        pc, po = sh(c), sh(o)
        bull_eng = (c > o) & (pc < po) & (c > po) & (o < pc)
        bear_eng = (c < o) & (pc > po) & (c < po) & (o > pc)
        bdiv = ph * 0 + (pl & (l3 < l6) & (r3 > r6) & (r3 < 40))
        sdiv = ph & (h3 > h6) & (r3 < r6) & (r3 > 60)
        lg = (rsi > r1) & (rsi < 50) & (rsi > 18) & (c > ema9) & (lo5 <= lo)
        lb = ((c > lo) & (pc <= lo)).astype(int) + (hammer | bull_eng | (doji & (c > o) & (lw > uw))) + bdiv + (v > vavg * 1.2) + (c > ema50)
        sg = (rsi < r1) & (rsi > 55) & (rsi < 82) & (c < ema9) & (hi5 >= up)
        sb = ((c < up) & (pc >= up)).astype(int) + (grave | bear_eng | (doji & (c < o) & (uw > lw))) + sdiv + (v > vavg * 1.2) + (c < ema50)
        lc = np.where(lg, lb, -1)
        sc = np.where(sg, sb, -1)
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
            out.append(("entry", 1))
            lev[i] = (ls_, lt_)
            S["tt"] += 1
        if pos == 0 and can0 and sc[i] >= minc:
            ss_, st_ = c[i] + (atr[i] * 1.5), c[i] - (atr[i] * 1.5 * 2.0)
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
    for params, mc, asn in (({}, 2, False), ({"Min Bonus Confirmations (on top of gates)": 3, "Trade Asian Session (21:00-01:30 GMT) - Caution": True}, 3, True)):
        ok, m = one(df, params, mc, asn)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
