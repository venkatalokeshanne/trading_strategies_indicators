"""Independent check — Europon Reversal FX Rush Ver2 (8LSSyeLc): hourly bars (24 h synthetic, price ~1.1) of a crypto-style symbol, market orders at the next open, default quantity 1, pyramiding 3, commission / slippage / margin off.
RSI(3) of two bars ago against the 40 / 60 levels inside the server-time trade hours (01-09 at Europe/Nicosia) buys / sells; a signal against an open position closes it and reverses. Nanpin adds (previous candle bullish for longs / bearish for shorts, shifted RSI under 30 for the 2nd and 20 for the 3rd position; mirrored 65 / 70 for shorts) are decided by the number of open lots.
Every bar re-issues one exit order per side at average entry +/- price unit x request (stop and limit). Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too.
Variants: defaults with a price unit of 0.002; levels 45 / 55 with a price unit of 0.004 and 3 / 5 requests; the all-day trade-hour filter off."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_rsi, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "8LSSyeLc"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    rsi = np_rsi(c, 3)
    sh = np.r_[np.full(2, np.nan), rsi[:-2]]
    hour = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Europe/Nicosia").dt.hour.to_numpy()
    ih = (hour >= 1) & (hour <= 9) if p["hf"] else np.ones(n, bool)
    lo, hi = p["lo"], p["hi"]
    lv2, lv3 = lo - lo / 4.0, lo - lo / 2.0
    sv2, sv3 = hi + (100.0 - hi) / 4.0, hi + (100.0 - hi) / 2.0

    def orders(i, info):
        out = []
        pos, avg, k = info["pos"], info["avg"], info["n"]
        prevbull = i > 0 and o[i - 1] < c[i - 1]
        prevbear = i > 0 and o[i - 1] > c[i - 1]
        with np.errstate(invalid="ignore"):
            r = sh[i]
            buy = ih[i] and r < lo
            sell = ih[i] and r > hi
            ln2, ln3 = ih[i] and prevbull and r < lv2, ih[i] and prevbull and r < lv3
            sn2, sn3 = ih[i] and prevbear and r > sv2, ih[i] and prevbear and r > sv3
        if buy and pos < 0:
            out += [("close", "Short"), ("entry", "Long", 1, 1.0)]
        elif buy and pos == 0:
            out.append(("entry", "Long", 1, 1.0))
        if sell and pos > 0:
            out += [("close", "Long"), ("entry", "Short", -1, 1.0)]
        elif sell and pos == 0:
            out.append(("entry", "Short", -1, 1.0))
        if pos > 0 and k < 3:
            if (k == 1 and ln2) or (k == 2 and ln3):
                out.append(("entry", "Long", 1, 1.0))
        if pos < 0 and k < 3:
            if (k == 1 and sn2) or (k == 2 and sn3):
                out.append(("entry", "Short", -1, 1.0))
        sd, td = p["pu"] * p["slr"], p["pu"] * p["tpr"]
        if pos > 0:
            out.append(("exit", "Long Exit", "Long", None, avg - sd, avg + td))
        if pos < 0:
            out.append(("exit", "Short Exit", "Short", None, avg + sd, avg - td))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=3)
    sym = SymbolInfo.make("BINANCE:XYZUSDT", "crypto", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(lo=40.0, hi=60.0, pu=0.01, slr=4.0, tpr=4.0, hf=True)


def check():
    df = bars(30000, seed=321, freq="1h")
    base = df["close"].iloc[0]
    for k in ("open", "high", "low", "close"):
        df[k] = 1.1 * (df[k] / base) ** 0.1
    msgs, allok = [], True
    cases = (({"Price Unit": 0.002}, dict(pu=0.002)),
             ({"RSI Low Level": 45.0, "RSI High Level": 55.0, "Price Unit": 0.004, "Stop Loss Request": 3.0, "Take Profit Request": 5.0}, dict(lo=45.0, hi=55.0, pu=0.004, slr=3.0, tpr=5.0)),
             ({"Use Trade Hour Filter": False, "Price Unit": 0.002}, dict(hf=False, pu=0.002)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
