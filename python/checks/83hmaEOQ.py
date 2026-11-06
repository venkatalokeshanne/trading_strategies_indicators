"""Independent check — Tomukas Elite SMC (83hmaEOQ): 5-minute bars (24 h synthetic, drift-free, price ~100) of a stock-style symbol, 20 shares per entry (the 10 %-of-equity sizing replaced), market orders at the next open, commission / slippage off.
The 200 EMA trend, the source's own ADX (RMA of ta.tr with na on the first bar, +DM / -DM, dx guard), the UTC-4 08:00-17:00 session, 5-bar swing levels, the rejection-candle liquidity sweeps, the market-structure shift with its fair-value gap, gap invalidation, the entry into the gap, the 1 R half take-profit that moves the stop to break-even and the opposite-sweep / EMA-cross runner exits are restated bar by bar.
Uses the quantity-aware bracket reference (indep.simulate_brackets with a partial exit leg). Variants: defaults; ADX threshold 10, 5-bar swings -> 3 and R:R 1.5."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_ema, np_rma, np_tr, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "83hmaEOQ"
QTY = 20.0


def pivots(x, left, right, high):
    out = np.full(len(x), False)
    for i in range(left + right, len(x)):
        w = x[i - left - right:i + 1]
        ctr = w[left]
        a, b = w[:left], w[left + 1:]
        out[i] = ((a < ctr).all() and (b <= ctr).all()) if high else ((a > ctr).all() and (b >= ctr).all())
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    utc = pd.to_datetime(df["time"], unit="ms", utc=True) - pd.Timedelta(hours=4)
    mins = (utc.dt.hour * 60 + utc.dt.minute).to_numpy()
    sess = (mins >= 480) & (mins < 1020)
    ema = np_ema(c, 200)
    h1, l1 = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    trr = np_rma(np_tr(h, l, c, False), 14)
    with np.errstate(invalid="ignore", divide="ignore"):
        plus = np_rma(np.where(np.isnan(h - h1), np.nan, np.maximum(h - h1, 0.0)), 14)
        minus = np_rma(np.where(np.isnan(l1 - l), np.nan, np.maximum(l1 - l, 0.0)), 14)
        pdi, mdi = 100 * plus / trr, 100 * minus / trr
        den = np.where(pdi + mdi == 0, 1.0, pdi + mdi)
        dx = 100 * np.abs(pdi - mdi) / den
    adx = np_rma(dx, 14)
    ph, pl = pivots(h, p["sw"], p["sw"], True), pivots(l, p["sw"], p["sw"], False)
    S = dict(lph=np.nan, lpl=np.nan, st=0, ex=np.nan, mss=False, ft=np.nan, fb=np.nan, ep=np.nan, sl=np.nan, tp=np.nan, hit=False)

    def orders(i, info):
        out = []
        pos = info["pos"]
        if ph[i]:
            S["lph"] = h[i - p["sw"]]
        if pl[i]:
            S["lpl"] = l[i - p["sw"]]
        h2, l2 = (h[i - 2], l[i - 2]) if i >= 2 else (np.nan, np.nan)
        with np.errstate(invalid="ignore"):
            mid = (h[i] + l[i]) / 2
            sweep_l = bool(l[i] < S["lpl"] and c[i] > S["lpl"] and (c[i] > mid and (c[i] - l[i]) > (h[i] - c[i]) * 1.5))
            sweep_h = bool(h[i] > S["lph"] and c[i] < S["lph"] and (c[i] < mid and (h[i] - c[i]) > (c[i] - l[i]) * 1.5))
            if sweep_l:
                S["st"], S["ex"] = 1, l[i]
            if sweep_h:
                S["st"], S["ex"] = -1, h[i]
            if sweep_l or sweep_h:
                S["mss"], S["ft"], S["fb"] = False, np.nan, np.nan
            if S["st"] == 1 and not S["mss"]:
                if c[i] > S["lph"] and S["lph"] > S["ex"]:
                    S["mss"] = True
                    if l[i] > h2:
                        S["ft"], S["fb"] = l[i], h2
            if S["st"] == -1 and not S["mss"]:
                if c[i] < S["lpl"] and S["lpl"] < S["ex"]:
                    S["mss"] = True
                    if h[i] < l2:
                        S["ft"], S["fb"] = l2, h[i]
            trend = 1 if c[i] > ema[i] else -1 if c[i] < ema[i] else 0
            valid = bool(S["mss"] and not np.isnan(S["ft"]) and adx[i] > p["adx"] and sess[i])
            le = bool(valid and S["st"] == 1 and trend == 1 and l[i] <= S["ft"] and l[i] >= S["fb"])
            se = bool(valid and S["st"] == -1 and trend == -1 and h[i] >= S["fb"] and h[i] <= S["ft"])
            if not np.isnan(S["ft"]):
                if S["st"] == 1 and c[i] < S["fb"]:
                    S["ft"] = S["fb"] = np.nan
                if S["st"] == -1 and c[i] > S["ft"]:
                    S["ft"] = S["fb"] = np.nan
        if le and pos == 0:
            S["ep"], S["sl"] = c[i], S["ex"]
            S["tp"] = S["ep"] + (S["ep"] - S["sl"]) * p["rr"]
            out.append(("entry", "Buy", 1, QTY))
            S["ft"] = np.nan
        if se and pos == 0:
            S["ep"], S["sl"] = c[i], S["ex"]
            S["tp"] = S["ep"] - (S["sl"] - S["ep"]) * p["rr"]
            out.append(("entry", "Sell", -1, QTY))
            S["ft"] = np.nan
        if pos > 0:
            if not S["hit"] and h[i] >= S["tp"]:
                S["hit"], S["sl"] = True, S["ep"]
                out.append(("exit", "TP1", "Buy", 50.0, None, S["tp"]))
            out.append(("exit", "SL/BE", "Buy", None, S["sl"], None))
            if S["st"] == -1 or c[i] < ema[i]:
                out.append(("close", "Buy"))
        if pos < 0:
            if not S["hit"] and l[i] <= S["tp"]:
                S["hit"], S["sl"] = True, S["ep"]
                out.append(("exit", "TP1", "Sell", 50.0, None, S["tp"]))
            out.append(("exit", "SL/BE", "Sell", None, S["sl"], None))
            if S["st"] == 1 or c[i] > ema[i]:
                out.append(("close", "Sell"))
        if pos == 0:
            S["hit"], S["ep"] = False, np.nan
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=0.01, qty_step=1e-9)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


def check():
    df = bars(90000, seed=5, freq="5min")
    lc = np.log(df["close"].to_numpy() / 100)
    det = lc - np.polyval(np.polyfit(np.arange(len(lc)), lc, 1), np.arange(len(lc)))
    rel = {k: df[k].to_numpy() / df["close"].to_numpy() for k in ("open", "high", "low", "close")}
    for k in rel:
        df[k] = 100 * np.exp(0.4 * det) * rel[k] ** 0.4
    msgs, allok = [], True
    cases = (({}, dict(sw=5, adx=20, rr=1.0)),
             ({"ADX Threshold": 10, "Swing Length": 3, "TP1 Risk/Reward": 1.5}, dict(sw=3, adx=10, rr=1.5)))
    for params, ov in cases:
        ok, m = one(df, params, ov)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
