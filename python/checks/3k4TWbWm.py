"""Independent check — China A-Share Long Trend Resonance System (3k4TWbWm): 15-minute bars (24 h synthetic, price ~100) of a stock-style symbol, 100 shares per entry (the 100 %-of-equity sizing replaced), orders at the bar's close (process_orders_on_close), commission / slippage off.
Restated bar by bar: the chart-timeframe Supertrend state machine (up / dn / trend with hl2 and ATR 10, factor 3), the same state machine re-evaluated on daily bars for request.security (lookahead off), HMA(50), the custom ADX(12) (DM with na-free zeros, tr na on the first bar, RMA smoothing), the rising ADX / HMA and price-acceleration filters, cooling, entry at the close, the two partial closes (30 % each of the open size, same-id closes in one bar replace each other), the hard stop, stage-1 early exit, Chandelier stop and the Supertrend sell after the second target.
Uses the quantity-aware bracket reference (indep.simulate_brackets, on_close). Variants: defaults; ADX / HMA / acceleration filters off with cooling 2; Chandelier off, partial sizes 50 % / 20 %."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_ema, np_periods, np_rma, np_security_lookahead_off, np_wma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "3k4TWbWm"
QTY = 100.0


def hma(x, n):
    a, b = np_wma(x, int(n / 2)), np_wma(x, n)
    return np_wma(2 * a - b, int(np.floor(np.sqrt(n) + 0.5)))


def supertrend_trend(h, l, c, factor=3.0, n=10):
    atr = np_atr(h, l, c, n)
    src = (h + l) / 2
    m = len(c)
    up_prev = dn_prev = np.nan
    tr = 1
    out = np.full(m, np.nan)
    for i in range(m):
        up = src[i] - factor * atr[i]
        up1 = up if np.isnan(up_prev) else up_prev
        c1 = c[i - 1] if i else np.nan
        if c1 > up1:
            up = max(up, up1) if not (np.isnan(up) or np.isnan(up1)) else np.nan
        dn = src[i] + factor * atr[i]
        dn1 = dn if np.isnan(dn_prev) else dn_prev
        if c1 < dn1:
            dn = min(dn, dn1) if not (np.isnan(dn) or np.isnan(dn1)) else np.nan
        if tr == -1 and c[i] > dn1:
            tr = 1
        elif tr == 1 and c[i] < up1:
            tr = -1
        up_prev, dn_prev = up, dn
        out[i] = tr
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr = np_atr(h, l, c, 10)
    hm = hma(c, 50)
    h1, l1, c1 = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]], np.r_[np.nan, c[:-1]]
    with np.errstate(invalid="ignore"):
        upm, dnm = h - h1, l1 - l
        pdm = np.where((upm > dnm) & (upm > 0), upm, 0.0)
        mdm = np.where((dnm > upm) & (dnm > 0), dnm, 0.0)
        tr = np.fmax(np.fmax(h - l, np.abs(h - c1)), np.abs(l - c1))
        tr = np.where(np.isnan(h - c1) | np.isnan(l - c1), np.nan, tr)           # math.max with na is na
    s_tr, s_p, s_m = np_rma(tr, 12), np_rma(pdm, 12), np_rma(mdm, 12)
    with np.errstate(invalid="ignore", divide="ignore"):
        pdi, mdi = s_p / s_tr * 100, s_m / s_tr * 100
        dx = np.abs(pdi - mdi) / (pdi + mdi) * 100
    adx = np_rma(dx, 12)
    trend = supertrend_trend(h, l, c)
    pid, last_of = np_periods(df, 1440)
    g = pd.DataFrame({"pid": pid, "h": h, "l": l, "c": c}).groupby("pid")
    dtr = supertrend_trend(g["h"].max().to_numpy(), g["l"].min().to_numpy(), g["c"].last().to_numpy())
    dtrend = np_security_lookahead_off(dtr, pid, last_of)
    atr_hi = np.full(n, np.nan)
    for i in range(4, n):
        atr_hi[i] = np.max(atr[i - 4:i + 1]) if not np.isnan(atr[i - 4:i + 1]).any() else np.nan
    S = dict(prev=None, last_exit=None, ep=np.nan, ea=np.nan, t1=False, t2=False, hs=np.nan)

    def orders(i, info):
        out = []
        pos = info["pos"]
        pp = S["prev"]
        S["prev"] = pos
        with np.errstate(invalid="ignore"):
            cooling = S["last_exit"] is not None and (i - S["last_exit"] < p["cool"])
            accel = (h[i] - h1[i]) > atr[i] * 0.5
            trig = bool(dtrend[i] == 1 and c[i] > hm[i] and adx[i] > 17 and not cooling)
            if p["adx_slope"]:
                trig = trig and bool(i > 0 and adx[i] > adx[i - 1])
            if p["hma_slope"]:
                trig = trig and bool(i > 0 and hm[i] > hm[i - 1])
            if p["accel"]:
                trig = trig and bool(accel)
        if trig and pos == 0:
            out.append(("entry", "LONG", 1, QTY))
        is_long = pos > 0
        if info["lots"]:
            S["ep"] = info["lots"][0]["ep"]
        if is_long and pp is not None and pp == 0:
            S["ea"] = atr[i]
        if not is_long:
            S["ea"] = np.nan
        r = (c[i] - S["ep"]) / S["ea"] if is_long else np.nan
        if not is_long:
            S["t1"] = S["t2"] = False
        with np.errstate(invalid="ignore"):
            t1 = bool(is_long and h[i] >= S["ep"] + 1.5 * S["ea"] and not S["t1"])
            t2 = bool(is_long and h[i] >= S["ep"] + 3.0 * S["ea"] and not S["t2"])
        if t1:
            out.append(("close", "LONG", p["q1"]))
            S["t1"] = True
        if t2:
            out.append(("close", "LONG", p["q2"]))
            S["t2"] = True
        stage = 0 if not is_long else 1 if not S["t1"] else 2 if not S["t2"] else 3
        if stage == 3:
            S["hs"] = c[i] if np.isnan(S["hs"]) else max(S["hs"], c[i])
        else:
            S["hs"] = np.nan
        with np.errstate(invalid="ignore"):
            ch = S["hs"] - 3.0 * atr_hi[i]
            stop = S["ep"] - 2.0 * S["ea"]
            e1 = stage == 1 and r >= 2 and l[i] < S["ep"] + 2 * S["ea"]
            e2 = p["chand"] and stage == 3 and l[i] <= ch
            e3 = stage == 3 and trend[i] == -1 and i > 0 and trend[i - 1] == 1
            ex = bool((is_long and l[i] < stop) or e1 or e2 or e3)
        if ex:
            out.append(("close", "LONG"))
            S["last_exit"] = i
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, on_close=True, tick=0.01, qty_step=1e-9)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(cool=5, adx_slope=True, hma_slope=True, accel=True, chand=True, q1=30.0, q2=30.0)


def check():
    df = bars(60000, seed=131, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({}, {}),
             ({"ADX斜率过滤": False, "HMA斜率过滤": False, "价格加速过滤": False, "冷却周期": 2}, dict(adx_slope=False, hma_slope=False, accel=False, cool=2)),
             ({"启用吊灯止损": False, "TP1减仓%": 50.0, "TP2减仓%": 20.0}, dict(chand=False, q1=50.0, q2=20.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
