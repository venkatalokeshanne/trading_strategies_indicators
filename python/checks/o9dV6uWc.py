"""Independent check — EMA Trend + MTF Stochastic Strategy (o9dV6uWc): 5-minute bars (24 h synthetic, drift-free, price ~100) of a stock-style symbol, the script's own risk-based quantities (equity mirrored: initial capital + closed P&L + open P&L, unrounded), market orders at the next open, commission / slippage off.
The chart stochastic (11, 3, 3; the SMA smoothing summed like the engine's rolling sum because saturated values create exact ties), the 15-minute stochastic with its K / D lines passed through a 11-bar linear regression (lookahead off), the EMA 38/62 trend, the crossover triggers with the rising-K / K-over-D / HTF K-over-D conditions, the ATR(14) risk sizing, the break-even and ATR-trailing stop ratchet in R units, the stop exit order, the stochastic-fade / trend-flip / 60-bar time-stop closes are restated bar by bar.
Uses the quantity-aware bracket reference (indep.simulate_brackets). Variants: defaults; trend requirement off with long-only trading and a 30-bar time stop."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_cross_over, np_cross_under, np_ema, np_periods, np_security_lookahead_off, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "o9dV6uWc"


def sma_prefix(x, n):
    out = np.full(len(x), np.nan)
    psum = [0.0]
    pnan = [0]
    for i, v in enumerate(x):
        if i + 1 >= n and not np.isnan(v) and pnan[i] - pnan[i - (n - 1)] == 0:
            out[i] = (psum[i] - psum[i - (n - 1)] + v) / n
        psum.append(psum[-1] + (0.0 if np.isnan(v) else v))
        pnan.append(pnan[-1] + (1 if np.isnan(v) else 0))
    return out


def stoch(c, h, l, n):
    out = np.full(len(c), np.nan)
    for i in range(n - 1, len(c)):
        hi, lo = h[i - n + 1:i + 1].max(), l[i - n + 1:i + 1].min()
        if hi != lo:
            out[i] = 100 * (c[i] - lo) / (hi - lo)
    return out


def linreg(y, n):
    out = np.full(len(y), np.nan)
    xs = np.arange(n, dtype=float)
    sx, sxx = xs.sum(), (xs * xs).sum()
    den = n * sxx - sx * sx
    for i in range(n - 1, len(y)):
        w = y[i - n + 1:i + 1]
        if np.isnan(w).any():
            continue
        sy, sxy = w.sum(), (xs * w).sum()
        slope = (n * sxy - sx * sy) / den
        out[i] = (sy - slope * sx) / n + slope * (n - 1)
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ef, es = np_ema(c, 38), np_ema(c, 62)
    k = sma_prefix(stoch(c, h, l, 11), 3)
    d = sma_prefix(k, 3)
    pid, last_of = np_periods(df, 15)
    g = pd.DataFrame({"pid": pid, "h": h, "l": l, "c": c}).groupby("pid")
    kk = sma_prefix(stoch(g["c"].last().to_numpy(), g["h"].max().to_numpy(), g["l"].min().to_numpy(), 11), 3)
    dd = sma_prefix(kk, 3)
    mk = np_security_lookahead_off(linreg(kk, 11), pid, last_of)
    md = np_security_lookahead_off(linreg(dd, 11), pid, last_of)
    xu50, xd50 = np_cross_over(mk, 50.0), np_cross_under(md, 50.0)
    xdu, xku = np_cross_under(md, 80.0), np_cross_over(mk, 20.0)
    atr = np_atr(h, l, c, 14)
    log: list = []
    S = dict(ebar=None, ep=np.nan, esd=np.nan, stop=np.nan)

    def orders(i, info):
        out = []
        pos = info["pos"]
        eq = 10000.0 + sum(dd_ * (xp - ep) * q for dd_, _, ep, _, xp, q in log) + sum(x["d"] * x["q"] * (c[i] - x["ep"]) for x in info["lots"])
        with np.errstate(invalid="ignore"):
            tu, td = bool(ef[i] > es[i]), bool(ef[i] < es[i])
            dk = k[i] - k[i - 1] if i else np.nan
            sl_ = bool(xu50[i] and k[i] > 50 and dk > 0 and k[i] > d[i] and mk[i] > md[i])
            ss_ = bool(xd50[i] and k[i] < 50 and dk < 0 and k[i] < d[i] and mk[i] < md[i])
            lc = bool(sl_ and ((not p["trend"]) or tu) and p["dir"] != "short")
            sc = bool(ss_ and ((not p["trend"]) or td) and p["dir"] != "long")
        dist = atr[i] * 1.5
        qty = eq * 0.01 / dist if dist > 0 else 0.0
        if lc and pos <= 0 and qty > 0:
            S["esd"], S["stop"], S["ep"], S["ebar"] = dist, c[i] - dist, c[i], i
            out.append(("entry", "Long", 1, float(qty)))
        if sc and pos >= 0 and qty > 0:
            S["esd"], S["stop"], S["ep"], S["ebar"] = dist, c[i] + dist, c[i], i
            out.append(("entry", "Short", -1, float(qty)))
        if pos > 0 and not np.isnan(S["esd"]) and S["esd"] > 0:
            r = (c[i] - S["ep"]) / S["esd"]
            if r >= 1.5:
                S["stop"] = max(S["stop"], c[i] - atr[i] * 1.5)
            elif r >= 1.0:
                S["stop"] = max(S["stop"], S["ep"])
        if pos < 0 and not np.isnan(S["esd"]) and S["esd"] > 0:
            r = (S["ep"] - c[i]) / S["esd"]
            if r >= 1.5:
                S["stop"] = min(S["stop"], c[i] + atr[i] * 1.5)
            elif r >= 1.0:
                S["stop"] = min(S["stop"], S["ep"])
        if pos > 0:
            out.append(("exit", "Long Exit", "Long", None, float(S["stop"]), None))
            if xdu[i]:
                out.append(("close", "Long"))
            if td:
                out.append(("close", "Long"))
        if pos < 0:
            out.append(("exit", "Short Exit", "Short", None, float(S["stop"]), None))
            if xku[i]:
                out.append(("close", "Short"))
            if tu:
                out.append(("close", "Short"))
        if p["tb"] > 0 and pos != 0 and S["ebar"] is not None and (i - S["ebar"]) >= p["tb"]:
            out.append(("close_all",))
            S["ebar"] = None
        if pos == 0:
            S["ebar"], S["ep"], S["esd"], S["stop"] = None, np.nan, np.nan, np.nan
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=0.01, qty_step=1e-9, log=log)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, dd_ = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params,
                                       strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{dd_} (got {len(ref)})"


def check():
    df = bars(40000, seed=5, freq="5min")
    lc = np.log(df["close"].to_numpy() / 100)
    det = lc - np.polyval(np.polyfit(np.arange(len(lc)), lc, 1), np.arange(len(lc)))
    rel = {k: df[k].to_numpy() / df["close"].to_numpy() for k in ("open", "high", "low", "close")}
    for k in rel:
        df[k] = 100 * np.exp(0.4 * det) * rel[k] ** 0.4
    msgs, allok = [], True
    cases = (({}, dict(trend=True, dir="both", tb=60)),
             ({"Require EMA Trend Agreement?": False, "Trade Direction": "Long Only", "Max Bars In Trade (time stop, 0=off)": 30}, dict(trend=False, dir="long", tb=30)))
    for params, ov in cases:
        ok, m = one(df, params, ov)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
