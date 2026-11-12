"""Independent check — Strict Failed 2 + Daily Bias Only (cgT9ys8s): 15-minute bars (24 h synthetic, drift-free, price ~100) of a stock-style symbol, 1 contract per entry, orders at the bar's close (process_orders_on_close), commission / slippage off.
The chart "failed 2" (a run of >= 2 same-colour candles ended by a non-inside opposite candle that probes the mother bar's extreme without closing outside), the same pattern on daily bars (09:30 New York periods, lookahead off) with its previous-run length from a barssince recursion, the bias requirement, the already-passed-target skip, and the entry with stop at the signal bar's extreme and limit at the mother bar's other extreme are restated bar by bar.
Uses the quantity-aware bracket reference (indep.simulate_brackets, on_close). Variants: defaults; 3-candle runs, bias not required, stop buffer 5 ticks."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_periods, np_security_lookahead_off, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "cgT9ys8s"


def daily_f2(o, h, l, c, minc, bull):
    """The security function on one set of bars: True where the failed-2 pattern completes."""
    n = len(c)
    out = np.zeros(n)
    bs = np.nan
    prev_flag = None
    for i in range(n):
        bearish, bullish = c[i] < o[i], c[i] > o[i]
        flag = bool(bearish if bull else bullish)              # the colour of the run that has to end
        cur = 0.0 if not flag else (np.nan if np.isnan(bs) else bs + 1)
        prev_streak = bs if prev_flag is True else 0.0
        prev_flag, bs = flag, cur
        if i == 0:
            continue
        ended = (not np.isnan(prev_streak)) and prev_streak >= minc and (not flag) and prev_streak > 0
        inside = h[i] < h[i - 1] and l[i] > l[i - 1]
        if bull:
            out[i] = float(ended and (not inside) and bullish and l[i] < l[i - 1] and h[i] <= h[i - 1] and c[i] > l[i - 1] and c[i] < h[i - 1])
        else:
            out[i] = float(ended and (not inside) and bearish and h[i] > h[i - 1] and l[i] >= l[i - 1] and c[i] < h[i - 1] and c[i] > l[i - 1])
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    pid, last_of = np_periods(df, 1440)
    g = pd.DataFrame({"pid": pid, "o": o, "h": h, "l": l, "c": c}).groupby("pid")
    do, dh, dl, dc = g["o"].first().to_numpy(), g["h"].max().to_numpy(), g["l"].min().to_numpy(), g["c"].last().to_numpy()
    bull_b = np_security_lookahead_off(daily_f2(do, dh, dl, dc, p["minc"], True), pid, last_of)
    bear_b = np_security_lookahead_off(daily_f2(do, dh, dl, dc, p["minc"], False), pid, last_of)
    S = dict(up=0, dn=0)

    def orders(i, info):
        out = []
        ib, ibr = c[i] > o[i], c[i] < o[i]
        h1, l1 = (h[i - 1], l[i - 1]) if i else (np.nan, np.nan)
        inside = h[i] < h1 and l[i] > l1
        pu, pd_ = S["up"], S["dn"]
        if ib:
            S["dn"], S["up"] = 0, (1 if S["up"] == 0 else S["up"] + 1)
        elif ibr:
            S["up"], S["dn"] = 0, (1 if S["dn"] == 0 else S["dn"] + 1)
        else:
            S["up"] = S["dn"] = 0
        eb = pu >= p["minc"] and (not ib) and pu > 0
        ebr = pd_ >= p["minc"] and (not ibr) and pd_ > 0
        with np.errstate(invalid="ignore"):
            bf2 = bool(eb and (not inside) and ibr and h[i] > h1 and l[i] >= l1 and c[i] < h1 and c[i] > l1)
            uf2 = bool(ebr and (not inside) and ib and l[i] < l1 and h[i] <= h1 and c[i] > l1 and c[i] < h1)
            bias_l = (not p["bias"]) or bool(bull_b[i] == 1.0)
            bias_s = (not p["bias"]) or bool(bear_b[i] == 1.0)
            tl = uf2 and bias_l and (not h1 <= c[i])
            ts = bf2 and bias_s and (not l1 >= c[i])
        if tl:
            out += [("entry", "Long", 1, 1.0), ("exit", "Long Exit", "Long", None, l[i] - p["buf"] * 0.01, h1)]
        if ts:
            out += [("entry", "Short", -1, 1.0), ("exit", "Short Exit", "Short", None, h[i] + p["buf"] * 0.01, l1)]
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, on_close=True, tick=0.01, qty_step=1e-9)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


def check():
    df = bars(60000, seed=5, freq="15min")
    lc = np.log(df["close"].to_numpy() / 100)
    det = lc - np.polyval(np.polyfit(np.arange(len(lc)), lc, 1), np.arange(len(lc)))
    rel = {k: df[k].to_numpy() / df["close"].to_numpy() for k in ("open", "high", "low", "close")}
    for k in rel:
        df[k] = 100 * np.exp(0.6 * det) * rel[k] ** 0.6
    msgs, allok = [], True
    cases = (({}, dict(minc=2, bias=True, buf=0)),
             ({"Minimum Consecutive Candles": 3, "Require Daily Bias In Trade Direction": False, "Stop Buffer (ticks)": 5}, dict(minc=3, bias=False, buf=5)))
    for params, ov in cases:
        ok, m = one(df, params, ov)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
