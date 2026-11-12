"""Independent check — ICT + Price Action (qkKBIVg4): 15-minute bars on a forex-type symbol (trading day from 17:00 New York for the VWAP reset), market entries at the next open, one position, bracket (stop 1.5 ATR14, target 2.5 ATR14 from the signal close) attached and working from the fill bar. Kill zones 07-10 and 12-15 UTC; trend: close above (below) EMA200 with EMA50 above (below) it; VWAP (hlc3, daily reset) side; RSI14 < 70 (> 30); ICT setup: fair value gap (high two bars ago below this low / low two bars ago above this high), an order-block engulfing (previous bar bearish and close above its high / mirrored) or a pin bar on the previous bar (lower wick >= 66.7 % of the range with body <= 35 %). Slippage / commission off on the pinelib side.
Variants: defaults; VWAP filter off with RSI limits 60 / 40 and a 1 ATR stop."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "qkKBIVg4"


def one(df, params, use_vwap, ob, os_, slm):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    ema50, ema200, atr, rsi = np_ema(c, 50), np_ema(c, 200), np_atr(h, l, c, 14), np_rsi(c, 14)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    day = (ny.dt.tz_localize(None) - pd.Timedelta(hours=17)).dt.date.to_numpy()
    hr = pd.to_datetime(df["time"], unit="ms", utc=True).dt.hour.to_numpy()
    hl3 = (h + l + c) / 3
    vw = np.zeros(n)
    pv = vv = 0.0
    for i in range(n):
        if i == 0 or day[i] != day[i - 1]:
            pv = vv = 0.0
        pv += hl3[i] * v[i]
        vv += v[i]
        vw[i] = pv / vv
    rng, body = h - l, np.abs(c - o)
    uw, lw = h - np.maximum(o, c), np.minimum(o, c) - l
    bpin = (rng > 0) & (lw >= rng * 0.667) & (body <= rng * 0.35)
    spin = (rng > 0) & (uw >= rng * 0.667) & (body <= rng * 0.35)
    lev = {}

    def orders(i, pos):
        out = []
        if i < 2:
            return out
        kz = (7 <= hr[i] < 10) or (12 <= hr[i] < 15)
        with np.errstate(invalid="ignore"):
            bt = c[i] > ema200[i] and ema50[i] > ema200[i]
            st_ = c[i] < ema200[i] and ema50[i] < ema200[i]
            vb = (not use_vwap) or c[i] > vw[i]
            vs = (not use_vwap) or c[i] < vw[i]
            rl, rs = rsi[i] < ob, rsi[i] > os_
        bfvg, sfvg = h[i - 2] < l[i], l[i - 2] > h[i]
        bob = c[i - 1] < o[i - 1] and c[i] > h[i - 1]
        sob = c[i - 1] > o[i - 1] and c[i] < l[i - 1]
        ls = kz and bt and vb and rl and (bfvg or bob or bpin[i - 1]) and pos == 0
        ss = kz and st_ and vs and rs and (sfvg or sob or spin[i - 1]) and pos == 0
        if ls:
            out.append(("entry", 1))
            lev[i] = (c[i] - slm * atr[i], c[i] + 2.5 * atr[i])
        if ss:
            out.append(("entry", -1))
            lev[i] = (c[i] + slm * atr[i], c[i] - 2.5 * atr[i])
        return out

    stop = lambda i, pos, ep, eb: lev[eb - 1][0] if eb - 1 in lev else None
    tgt = lambda i, pos, ep, eb: lev[eb - 1][1] if eb - 1 in lev else None
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt)
    sym = SymbolInfo.make("OANDA:XAUUSD", "forex", mintick=0.01, qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides={"slippage": 0, "commission_value": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(30000, seed=404, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 2000 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    for params, args in (({}, (True, 70, 30, 1.5)),
                         ({"Enable VWAP Direction Filter": False, "Overbought Level": 60, "Oversold Level": 40, "Stop Loss  (× ATR)": 1.0}, (False, 60, 40, 1.0))):
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
