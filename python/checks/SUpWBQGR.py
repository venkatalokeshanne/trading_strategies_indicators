"""Independent check — Quant Scoring System Long Only (SUpWBQGR): 15-minute bars (24 h synthetic, drift-free, price ~100) of a crypto-style symbol (UTC), the script's own all-equity fractional quantities (equity mirrored: initial capital 92 + closed P&L + open P&L, not rounded: the engine passes an explicit quantity through), market orders at the next open, commission / slippage off.
EMA gap / momentum (1-bar ROC) / stretch from the VWMA / volume / regression-slope factors z-scored over 20 bars and clamped, the scaled score against the entry / exit thresholds and the EMA regime, the ATR / hard-percent stop with the (huge) target re-issued every bar, the runner mode after +8 % (hard stop only, close on the falling 4-hour EMA(50) with the close under it, lookahead off) and the base exit are restated bar by bar.
Uses the quantity-aware bracket reference (indep.simulate_brackets). Variants: defaults; leverage 2, entry threshold 1, runner trigger 2 %."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_ema, np_periods, np_security_lookahead_off, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "SUpWBQGR"


def rq(q, step=1e-9):
    n = q / step
    return np.floor(n + max(1e-9, abs(n) * 1e-12)) * step


def pstd(x, n):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        if not np.isnan(w).any():
            out[i] = np.std(w)
    return out


def norm(x, n):
    m, s = np_sma(x, n), pstd(x, n)
    with np.errstate(invalid="ignore", divide="ignore"):
        z = np.where(s == 0.0, 0.0, (x - m) / s)
    z = np.where(np.isnan(m) | np.isnan(s), np.nan, z)
    return np.clip(z, -3.0, 3.0) / 3.0


def linreg(y, n, offset):
    out = np.full(len(y), np.nan)
    xs = np.arange(n, dtype=float)
    sx, sxx = xs.sum(), (xs * xs).sum()
    den = n * sxx - sx * sx
    for i in range(n - 1, len(y)):
        w = y[i - n + 1:i + 1]
        sy, sxy = w.sum(), (xs * w).sum()
        slope = (n * sxy - sx * sy) / den
        out[i] = (sy - slope * sx) / n + slope * (n - 1 - offset)
    return out


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    ef, es = np_ema(c, 20), np_ema(c, 100)
    atr = np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore", divide="ignore"):
        trend = np.where(atr == 0.0, 0.0, np.clip((ef - es) / atr, -3.0, 3.0) / 3.0)
        c1 = np.r_[np.nan, c[:-1]]
        roc = 100 * (c - c1) / c1
        mom = norm(roc, 20)
        vw = np_sma(c * v, 20) / np_sma(v, 20)
        stretch = np.where(atr == 0.0, 0.0, (c - vw) / atr)
        mr = np.clip(-stretch, -3.0, 3.0) / 3.0
        volraw = pstd(np.log(c / c1), 10)
        volreg = norm(volraw, 20)
        volconf = norm(v, 20)
        slopen = norm(linreg(c, 20, 0) - linreg(c, 20, 1), 20)
        score = (0.20 * trend + 0.20 * mom + 0.10 * mr + 0.0 * volreg * np.sign(trend) + 0.10 * volconf * np.sign(mom) + 0.10 * slopen) * 7.0
    pid, last_of = np_periods(df, 240, start_minutes=0, tz="UTC")
    pc = pd.Series(c).groupby(pid).last().to_numpy()
    hc = np_security_lookahead_off(pc, pid, last_of)
    he = np_security_lookahead_off(np_ema(pc, 50), pid, last_of)
    he1 = np.r_[np.nan, he[:-1]]
    log: list = []
    S = dict(runner=False)

    def orders(i, info):
        out = []
        pos, avg = info["pos"], info["avg"]
        eq = 92.0 + sum(d * (xp - ep) * q for d, _, ep, _, xp, q in log) + sum(x["d"] * x["q"] * (c[i] - x["ep"]) for x in info["lots"])
        with np.errstate(invalid="ignore"):
            regime = bool(ef[i] > es[i] and c[i] > es[i])
            lsig = bool(score[i] > p["th"] and regime)
            base_exit = bool(score[i] < 0.0 or c[i] < ef[i])
            bear = bool(hc[i] < he[i] and he[i] < he1[i])
        qty = max(eq, 0) * p["lev"] / c[i] if c[i] > 0 else 0.0
        if lsig and pos == 0 and qty > 0:
            out.append(("entry", "Long", 1, float(qty)))
        if pos <= 0:
            S["runner"] = False
        if pos > 0 and not S["runner"] and h[i] >= avg * (1 + p["trig"] / 100.0):
            S["runner"] = True
        if pos > 0:
            hard = avg * (1.0 - 2.0 / 100.0)
            if S["runner"]:
                out.append(("exit", "Long Exit", "Long", None, hard, None))
                if bear:
                    out.append(("close", "Long"))
            else:
                out.append(("exit", "Long Exit", "Long", None, max(avg - 2.0 * atr[i], hard), avg + 300.5 * atr[i]))
                if base_exit:
                    out.append(("close", "Long"))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=0.01, qty_step=1e-9, log=log)
    sym = SymbolInfo.make("BINANCE:BTCUSDT", "crypto", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


def check():
    df = bars(40000, seed=5, freq="15min")
    lc = np.log(df["close"].to_numpy() / 100)
    det = lc - np.polyval(np.polyfit(np.arange(len(lc)), lc, 1), np.arange(len(lc)))
    rel = {k: df[k].to_numpy() / df["close"].to_numpy() for k in ("open", "high", "low", "close")}
    for k in rel:
        df[k] = 100 * np.exp(0.4 * det) * rel[k] ** 0.4
    msgs, allok = [], True
    cases = (({}, dict(th=2.0, lev=1.0, trig=8.0)),
             ({"Leverage": 2.0, "Long Score Threshold": 1.0, "Runner Trigger Profit %": 2.0}, dict(th=1.0, lev=2.0, trig=2.0)))
    for params, ov in cases:
        ok, m = one(df, params, ov)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
