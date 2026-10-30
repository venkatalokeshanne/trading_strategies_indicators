"""Independent check — Adaptive Multi-Factor Swing Strategy (VO1vEJJW): 3000 daily business-day bars (price ~100) of a stock-style symbol, 1 contract per entry, market orders at the next open, commission / slippage / margin off.
MACD(12, 26, 7), the stochastic with the source's argument order (source = high, "high" = low, "low" = close), momentum, RSI(7), the Vortex indicator by sliding sums of the history of the passed expressions, DMI(8), the custom MFI(10), the Fisher transform, the parabolic SAR (the reference-manual algorithm, step for step), the +-1 vote score, the chop-zone cool-down, the bankruptcy stop, and the entry / close rules (every bar, no flat gate; opposite entries reverse) are restated bar by bar.
Uses the quantity-aware bracket reference (indep.simulate_brackets). Variants: defaults; thresholds 2 / 0 / -2 / 0 with a 10-bar cool-down."""
import numpy as np

from indep import bars, compare_q, np_atr, np_dmi, np_ema, np_rsi, np_sma, np_tr, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "VO1vEJJW"


def wfn(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


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


def slide(x, n):
    x = np.where(np.isnan(x), 0.0, x)
    out = np.zeros(len(x))
    for i in range(len(x)):
        out[i] = x[max(0, i - n + 1):i + 1].sum()
    return out


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    macd = np_ema(c, 12) - np_ema(c, 26)
    sg = np_ema(macd, 7)
    hh, ll = wfn(l, 14, np.max), wfn(c, 14, np.min)
    with np.errstate(invalid="ignore", divide="ignore"):
        k = 100 * (h - ll) / (hh - ll)
    d = np_sma(k, 3)
    mom = c - np.r_[[np.nan] * 10, c[:-10]]
    rsi = np_rsi(c, 7)
    ps = sar(h, l, c, 0.0, 0.02, 0.2)
    atr = np_atr(h, l, c, 14)
    atr_ma = np_sma(atr, 20)
    pdi, mdi, adx = np_dmi(h, l, c, 8)
    l1, h1 = np.r_[0.0, l[:-1]], np.r_[0.0, h[:-1]]
    vmp, vmm, trs = slide(np.abs(h - l1), 8), slide(np.abs(l - h1), 8), slide(np_tr(h, l, c, False), 8)
    with np.errstate(invalid="ignore", divide="ignore"):
        vip, vim = np.where(trs != 0, vmp / trs, 0), np.where(trs != 0, vmm / trs, 0)
    tp = (h + l + c) / 3
    tp1 = np.r_[0.0, tp[:-1]]
    raw = tp * v
    pos_s, neg_s = slide(np.where(tp > tp1, raw, 0.0), 10), slide(np.where(tp < tp1, raw, 0.0), 10)
    with np.errstate(invalid="ignore", divide="ignore"):
        mfi = np.where(neg_s == 0, 100.0, 100 - 100 / (1 + pos_s / neg_s))
    hi, lo = wfn(c, 10, np.max), wfn(c, 10, np.min)
    with np.errstate(invalid="ignore", divide="ignore"):
        vv = np.where(hi != lo, (c - lo) / (hi - lo), 0.5)
    vv = np.maximum(np.minimum(vv, 0.999), 0.001)
    fish = 0.5 * np.log(vv / (1 - vv))
    fsig = np_sma(fish, 6)
    S = dict(stop=None, bankrupt=False)
    log: list = []

    def orders(i, info):
        out = []
        eq = 100000.0 + sum(dd * (xp - ep) * q for dd, _, ep, _, xp, q in log) + sum(x["d"] * x["q"] * (c[i] - x["ep"]) for x in info["lots"])
        with np.errstate(invalid="ignore"):
            sc = (1 if macd[i] > sg[i] else -1) + (1 if k[i] > d[i] else -1) + (1 if mom[i] > 0 else -1) + (1 if rsi[i] > 50 else -1) + (1 if vip[i] > vim[i] else -1) + (1 if pdi[i] > mdi[i] else -1) + (1 if mfi[i] > 50 else -1) + (1 if fish[i] > fsig[i] else -1)
            chop = bool(adx[i] < 10 and atr[i] > atr_ma[i])
        if chop:
            S["stop"] = i + p["cool"]
        allowed = S["stop"] is None or i > S["stop"]
        if (not S["bankrupt"]) and eq <= 100000.0 * 0.5:
            S["bankrupt"] = True
            out.append(("close_all",))
        with np.errstate(invalid="ignore"):
            le = sc >= p["lth"] and ps[i] < c[i] and rsi[i] < 100
            lx = sc <= p["lxt"] or ps[i] > c[i]
            se = sc <= p["sth"] and ps[i] > c[i] and rsi[i] > 30
            sx = sc >= p["sxt"] or ps[i] < c[i]
        if le and not S["bankrupt"] and allowed:
            out.append(("entry", "LONG", 1, 1.0))
        if lx:
            out.append(("close", "LONG"))
        if se and not S["bankrupt"] and allowed:
            out.append(("entry", "SHORT", -1, 1.0))
        if sx:
            out.append(("close", "SHORT"))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=0.01, qty_step=1e-9, log=log)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, dd = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{dd} (got {len(ref)})"


def check():
    df = bars(3000, seed=5, freq="B")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({}, dict(lth=4, lxt=1, sth=-6, sxt=-2, cool=50)),
             ({"longScoreTh": 2, "longExitTh": 0, "shortScoreTh": -2, "shortExitTh": 0, "Cooldown Bars": 10}, dict(lth=2, lxt=0, sth=-2, sxt=0, cool=10)))
    for params, ov in cases:
        ok, m = one(df, params, ov)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
