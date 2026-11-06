"""Independent check — Trend Pivot Scale In (rSachA35): hourly bars of a stock-style symbol, market orders at the next open, cash-sized entries (10, 10, 20, 40, 80 / close), pyramiding 5, commission / slippage / margin off.
Buy = a pivot low confirmed on this bar (left = right = strength) while close > EMA200, +DI > -DI, ADX > min (mirror for sells). The script's add counters reset when flat; a buy is allowed while the position is flat or long and (flat, or close below the average entry price); the counter increments whenever the entry is called.
One exit order for all lots (limit at the average entry price +/- ATR x 3 / 2 / 1.5 / 1.2 depending on the number of open lots) is re-issued each bar. Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too.
Variants: defaults with EMA 50 and ADX 15; pivot strength 4, EMA 50, ADX 10; pivot strength 3, EMA 20, no ADX filter (ADX 0)."""
import numpy as np

from indep import bars, compare_q, np_atr, np_dmi, np_ema, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "rSachA35"
CASH = (10.0, 10.0, 20.0, 40.0, 80.0)


def pivots(x, k, high):
    n = len(x)
    out = np.full(n, np.nan)
    for i in range(2 * k, n):
        m = i - k
        c = x[m]
        lw, rw = x[m - k:m], x[m + 1:i + 1]
        ok = (np.all(c > lw) and np.all(c >= rw)) if high else (np.all(c < lw) and np.all(c <= rw))
        if ok:
            out[i] = c
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    ema = np_ema(c, p["ema"])
    pdi, mdi, adx = np_dmi(h, l, c, 14)
    atr = np_atr(h, l, c, 14)
    pl, ph = pivots(l, p["pv"], False), pivots(h, p["pv"], True)
    S = dict(la=0, sa=0)

    def orders(i, info):
        out = []
        pos, avg, k = info["pos"], info["avg"], info["n"]
        with np.errstate(invalid="ignore"):
            bull = c[i] > ema[i] and pdi[i] > mdi[i] and adx[i] > p["adx"]
            bear = c[i] < ema[i] and mdi[i] > pdi[i] and adx[i] > p["adx"]
        buy = bull and not np.isnan(pl[i])
        sell = bear and not np.isnan(ph[i])
        if pos == 0:
            S["la"] = S["sa"] = 0
        if buy and S["la"] < 5 and pos >= 0:
            if pos == 0 or c[i] < avg:
                out.append(("entry", "BUY %d" % (S["la"] + 1), 1, CASH[S["la"]] / c[i]))
                S["la"] += 1
        if sell and S["sa"] < 5 and pos <= 0:
            if pos == 0 or c[i] > avg:
                out.append(("entry", "SELL %d" % (S["sa"] + 1), -1, CASH[S["sa"]] / c[i]))
                S["sa"] += 1
        mult = 3.0
        if k == 2:
            mult = 2.0
        if k == 3:
            mult = 1.5
        if k >= 4:
            mult = 1.2
        if pos > 0:
            out.append(("exit", "LONG EXIT", "", None, None, avg + atr[i] * mult))
        if pos < 0:
            out.append(("exit", "SHORT EXIT", "", None, None, avg - atr[i] * mult))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=5)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(ema=200, pv=8, adx=25)


def check():
    df = bars(30000, seed=281, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({"EMA": 50, "Min ADX": 15}, dict(ema=50, adx=15)),
             ({"EMA": 50, "Pivot Strength": 4, "Min ADX": 10}, dict(ema=50, pv=4, adx=10)),
             ({"EMA": 20, "Pivot Strength": 3, "Min ADX": 0}, dict(ema=20, pv=3, adx=0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
