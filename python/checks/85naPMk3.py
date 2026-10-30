"""Independent check — VuManChu WT Zero Cross V1.1b (85naPMk3): 5-minute bars (24 h synthetic, price ~100) of a stock-style symbol, 10 shares per entry (the 2 %-of-equity sizing replaced), orders at the bar's close (process_orders_on_close), commission / slippage off.
WaveTrend wt1 (EMA of the channel index of hlc3, 9 / 27) zero crosses with the optional 200 EMA side, the opposite position closed before the entry, and the stop at the 10-minute (twice the chart) parabolic SAR (reference-manual algorithm on the aggregated 10-minute bars, lookahead off) re-issued every bar are restated bar by bar.
Uses the quantity-aware bracket reference (indep.simulate_brackets, on_close). Variants: defaults; EMA filter on with SAR timeframe 15 minutes."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_cross_over, np_cross_under, np_ema, np_periods, np_security_lookahead_off, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "85naPMk3"
QTY = 10.0


def sar(h, l, c, start, inc, mx):
    n = len(c)
    out = np.full(n, np.nan)
    result = maxmin = accel = np.nan
    below = False
    for i in range(n):
        first = False
        if i == 1:
            if c[i] > c[i - 1]:
                below, maxmin, result = True, h[i], l[i - 1]
            else:
                below, maxmin, result = False, l[i], h[i - 1]
            first = True
            accel = start
        if i >= 1:
            result = result + accel * (maxmin - result)
            if below:
                if result > l[i]:
                    first, below, result, maxmin, accel = True, False, max(h[i], maxmin), l[i], start
            else:
                if result < h[i]:
                    first, below, result, maxmin, accel = True, True, min(l[i], maxmin), h[i], start
            if not first:
                if below:
                    if h[i] > maxmin:
                        maxmin, accel = h[i], min(accel + inc, mx)
                else:
                    if l[i] < maxmin:
                        maxmin, accel = l[i], min(accel + inc, mx)
            if below:
                result = min(result, l[i - 1])
                if i > 1:
                    result = min(result, l[i - 2])
            else:
                result = max(result, h[i - 1])
                if i > 1:
                    result = max(result, h[i - 2])
            out[i] = result
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    src = (h + l + c) / 3
    esa = np_ema(src, 9)
    de = np_ema(np.abs(src - esa), 9)
    with np.errstate(invalid="ignore", divide="ignore"):
        ci = (src - esa) / (0.015 * de)
    wt1 = np_ema(ci, 27)
    lu, ld = np_cross_over(wt1, 0.0), np_cross_under(wt1, 0.0)
    e200 = np_ema(c, 200)
    pid, last_of = np_periods(df, p["tf"])
    g = pd.DataFrame({"pid": pid, "h": h, "l": l, "c": c}).groupby("pid")
    ps = np_security_lookahead_off(sar(g["h"].max().to_numpy(), g["l"].min().to_numpy(), g["c"].last().to_numpy(), 0.0075, 0.0075, 0.075), pid, last_of)

    def orders(i, info):
        out = []
        pos = info["pos"]
        with np.errstate(invalid="ignore"):
            la = (not p["filter"]) or c[i] > e200[i]
            sa = (not p["filter"]) or c[i] < e200[i]
        if lu[i] and la:
            if pos < 0:
                out.append(("close", "Short"))
            out.append(("entry", "Long", 1, QTY))
        if ld[i] and sa:
            if pos > 0:
                out.append(("close", "Long"))
            out.append(("entry", "Short", -1, QTY))
        stop = None if np.isnan(ps[i]) else float(ps[i])
        out.append(("exit", "Long Stop", "Long", None, stop, None))
        out.append(("exit", "Short Stop", "Short", None, stop, None))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, on_close=True, tick=0.01, qty_step=1e-9)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


def check():
    df = bars(30000, seed=5, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.2
    msgs, allok = [], True
    cases = (({}, dict(filter=False, tf=10)),
             ({"Enable EMA Filter": True, "PSAR Timeframe": "15"}, dict(filter=True, tf=15)))
    for params, ov in cases:
        ok, m = one(df, params, ov)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
