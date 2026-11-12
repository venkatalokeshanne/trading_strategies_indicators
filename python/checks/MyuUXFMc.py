"""Independent check — Crypto Swing EMA Colour Strategy Plus (MyuUXFMc): 4-hour bars (6-per-day synthetic, price ~100) of a crypto-style symbol (UTC), 10 units per entry (the 95 %-of-equity sizing replaced), market orders at the next open, commission / slippage off.
EMA(200) colour change confirmed beyond an ATR / percent buffer for N bars (barssince) or the raw cross, the minimum bars between entries, entries in the date window (2021-01-01 .. end), the long exit on the red change, the short exit on the "sell" setup (MACD histogram cross-under, RSI 50-80, MFI > 50), the ATR emergency stops, the two 50 % short take-profit legs, the capitulation exit (ATR move, oversold RSI / stochastic, stochastic %K cross-over D) and the out-of-window close_all are restated bar by bar.
Uses the quantity-aware bracket reference (indep.simulate_brackets with partial exit legs). Variants: defaults; raw cross, no ATR stop; end date 2023-01-01 with percent buffer and no short take profits."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_cross_over, np_cross_under, np_ema, np_rsi, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "MyuUXFMc"
QTY = 10.0


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


def mfi(src, vol, n):
    ch = np.r_[np.nan, np.diff(src)]
    up = np.where(ch <= 0, 0.0, src) * vol
    dn = np.where(ch >= 0, 0.0, src) * vol
    out = np.full(len(src), np.nan)
    for i in range(n, len(src)):
        u, d = up[i - n + 1:i + 1].sum(), dn[i - n + 1:i + 1].sum()
        out[i] = 100 - 100 / (1 + u / d) if d != 0 else (100.0 if u > 0 else np.nan)
    return out


def barssince(cond):
    out = np.full(len(cond), np.nan)
    last = None
    for i, v in enumerate(cond):
        if v:
            last = i
        if last is not None:
            out[i] = i - last
    return out


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    t = df["time"].to_numpy()
    start = int(pd.Timestamp("2021-01-01", tz="UTC").timestamp() * 1000)
    ema = np_ema(c, 200)
    rsi = np_rsi(c, 14)
    mf = mfi((h + l + c) / 3, v, 14)
    macd = np_ema(c, 12) - np_ema(c, 26)
    hist = macd - np_ema(macd, 9)
    hu, hd = np_cross_over(hist, 0.0), np_cross_under(hist, 0.0)
    atr = np_atr(h, l, c, 14)
    buf = atr * 0.35 if p["buf"] == "ATR" else ema * 0.6 / 100
    above, below = c > ema + buf, c < ema - buf
    ca = barssince(~above) >= 1
    cb = barssince(~below) >= 1
    xu, xd = np_cross_over(c, ema), np_cross_under(c, ema)
    sk = sma_prefix(sma_prefix(stoch(c, h, l, 14), 3), 3)
    k_ = sma_prefix(stoch(c, h, l, 14), 3)
    d_ = sma_prefix(k_, 3)
    sbc = np_cross_over(k_, d_)
    S = dict(last=None, ca_prev=False, cb_prev=False)

    def orders(i, info):
        out = []
        pos, avg = info["pos"], info["avg"]
        inwin = t[i] >= start and t[i] <= p["end"]
        with np.errstate(invalid="ignore"):
            sell = bool(c[i] < ema[i] and hd[i] and rsi[i] > 50 and rsi[i] < 80 and mf[i] > 50)
        enough = S["last"] is None or i - S["last"] >= 8
        if p["aw"]:
            green = bool(ca[i]) and not S["ca_prev"] and enough
            red = bool(cb[i]) and not S["cb_prev"] and enough
        else:
            green, red = bool(xu[i]) and enough, bool(xd[i]) and enough
        S["ca_prev"], S["cb_prev"] = bool(ca[i]), bool(cb[i])
        if inwin and pos <= 0 and green:
            out.append(("entry", "Long", 1, QTY))
            S["last"] = i
        if inwin and pos >= 0 and red:
            out.append(("entry", "Short", -1, QTY))
            S["last"] = i
        if pos > 0 and red:
            out.append(("close", "Long"))
        if pos < 0 and sell:
            out.append(("close", "Short"))
        if not inwin:
            out.append(("close_all",))
        with np.errstate(invalid="ignore"):
            move = (avg - c[i]) / atr[i] if pos < 0 else 0.0
            cap = bool(pos < 0 and move >= 5.0 and (rsi[i] <= 28 or k_[i] <= 20) and sbc[i])
        if pos > 0 and p["stop"]:
            out.append(("exit", "Long ATR Stop", "Long", None, avg - atr[i] * 4.0, None))
        if pos < 0:
            ss, t1, t2 = avg + atr[i] * 4.0, avg - atr[i] * 4.0, avg - atr[i] * 7.0
            if p["tp"] and p["stop"]:
                out += [("exit", "Short TP1/SL", "Short", 50.0, ss, t1), ("exit", "Short TP2/SL", "Short", 50.0, ss, t2)]
            elif p["tp"]:
                out += [("exit", "Short TP1", "Short", 50.0, None, t1), ("exit", "Short TP2", "Short", 50.0, None, t2)]
            elif p["stop"]:
                out.append(("exit", "Short ATR Stop", "Short", None, ss, None))
            if cap:
                out.append(("close", "Short"))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=0.01, qty_step=1e-9)
    sym = SymbolInfo.make("BINANCE:BTCUSDT", "crypto", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="240", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


def check():
    df = bars(20000, seed=161, freq="4h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.4
    far = int(pd.Timestamp("2030-01-01", tz="UTC").timestamp() * 1000)
    end23 = int(pd.Timestamp("2023-01-01", tz="UTC").timestamp() * 1000)
    msgs, allok = [], True
    cases = (({}, dict(buf="ATR", aw=True, stop=True, tp=True, end=far)),
             ({"Use anti-whipsaw EMA buffer": False, "Use ATR emergency stop": False}, dict(buf="ATR", aw=False, stop=False, tp=True, end=far)),
             ({"Backtest end": end23, "Buffer type": "Percent", "Use short take profits": False}, dict(buf="Percent", aw=True, stop=True, tp=False, end=end23)))
    for params, ov in cases:
        ok, m = one(df, params, ov)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
