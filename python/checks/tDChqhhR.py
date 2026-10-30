"""Independent check — Auto-Trade Bot v12 EMA115 (tDChqhhR): 5-minute bars (24 h synthetic, price ~100) of a stock-style symbol, fixed quantity (the 100 %-of-equity sizing replaced), market orders at the next open, commission / slippage off.
Liquidity sweeps against the lowest low / highest high of the previous N bars arm a setup; the confirming candle must close beyond the sweep bar, above / below the HMA (floor-length WMA chain) that is rising / falling for two bars, above / below the hourly EMA(115) (lookahead off) that is rising / falling for two chart bars; Williams %R vs its EMA(13) with the oversold / overbought history window (HP) or the higher-low / lower-high rule (LP). Stop beyond the sweep bar by one tick (0.5 % fallback) and a target R:R times the risk, re-issued every bar while in the trade.
Uses the quantity-aware bracket reference (indep.simulate_brackets). Variants: longs only; both sides with a 8-bar sweep, R:R 2, oversold -70."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_ema, np_periods, np_security_lookahead_off, np_wma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "tDChqhhR"
QTY = 10.0
TICK = 0.01


def wfn(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        out[i] = fn(w) if not np.isnan(w).any() else np.nan
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    hma = np_wma(2 * np_wma(c, 10) - np_wma(c, 20), 4)
    pid, last_of = np_periods(df, 60)
    pc = pd.Series(c).groupby(pid).last().to_numpy()
    ema = np_security_lookahead_off(np_ema(pc, 115), pid, last_of)
    hh, ll = wfn(h, 14, np.max), wfn(l, 14, np.min)
    with np.errstate(invalid="ignore", divide="ignore"):
        wr = 100.0 * (c - hh) / (hh - ll)
    wema = np_ema(wr, 13)
    l1, h1 = np.r_[np.nan, l[:-1]], np.r_[np.nan, h[:-1]]
    swl, swh = wfn(l1, p["sweep"], np.min), wfn(h1, p["sweep"], np.max)
    ob = -(100 + p["os"])
    S = dict(los=-1000, lob=-1000, lsh=np.nan, lsl=np.nan, lon=False, ssl=np.nan, ssh=np.nan, son=False, lls=np.nan, pls=np.nan, lsh2=np.nan, psh=np.nan, tsl=np.nan, ttp=np.nan)

    def orders(i, info):
        out = []
        pos = info["pos"]
        with np.errstate(invalid="ignore"):
            if wr[i] <= p["os"]:
                S["los"] = i
            if wr[i] >= ob:
                S["lob"] = i
            from_os, from_ob = (i - S["los"]) <= 70, (i - S["lob"]) <= 70
            ils = l[i] < swl[i]
            if ils:
                S["lsh"], S["lsl"], S["lon"] = h[i], l[i], True
            iss = h[i] > swh[i]
            if iss:
                S["ssl"], S["ssh"], S["son"] = l[i], h[i], True
            if ils:
                S["pls"], S["lls"] = S["lls"], l[i]
            if iss:
                S["psh"], S["lsh2"] = S["lsh2"], h[i]
            hl = (not np.isnan(S["pls"])) and S["lls"] > S["pls"]
            lh = (not np.isnan(S["psh"])) and S["lsh2"] < S["psh"]
            h1_, h2_ = (hma[i - 1], hma[i - 2]) if i >= 2 else (np.nan, np.nan)
            e1_, e2_ = (ema[i - 1], ema[i - 2]) if i >= 2 else (np.nan, np.nan)
            hrise, hfall = hma[i] >= h1_ and h1_ >= h2_, hma[i] <= h1_ and h1_ <= h2_
            erise, efall = ema[i] >= e1_ and e1_ >= e2_, ema[i] <= e1_ and e1_ <= e2_
            lbase = bool(S["lon"] and c[i] > o[i] and c[i] > S["lsh"] and c[i] > hma[i] and hrise and c[i] > ema[i] and erise)
            if lbase:
                S["lon"] = False
            lsig = lbase and wr[i] > wema[i] and (from_os or hl)
            sbase = bool((not p["longs_only"]) and S["son"] and c[i] < o[i] and c[i] < S["ssl"] and c[i] < hma[i] and hfall and c[i] < ema[i] and efall)
            if sbase:
                S["son"] = False
            ssig = sbase and wr[i] < wema[i] and (from_ob or lh)
        lsl_ = S["lsl"] - TICK if not np.isnan(S["lsl"]) else c[i] * 0.995
        ltp = c[i] + max(c[i] - lsl_, TICK) * p["rr"]
        ssl_ = S["ssh"] + TICK if not np.isnan(S["ssh"]) else c[i] * 1.005
        stp = c[i] - max(ssl_ - c[i], TICK) * p["rr"]
        if lsig and pos == 0:
            S["tsl"], S["ttp"] = lsl_, ltp
            out.append(("entry", "Long", 1, QTY))
        if ssig and pos == 0:
            S["tsl"], S["ttp"] = ssl_, stp
            out.append(("entry", "Short", -1, QTY))
        if pos > 0:
            out.append(("exit", "Exit Long", "Long", None, S["tsl"], S["ttp"]))
        if pos < 0:
            out.append(("exit", "Exit Short", "Short", None, S["tsl"], S["ttp"]))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=TICK, qty_step=1e-9)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


def check():
    df = bars(40000, seed=5, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.2
    msgs, allok = [], True
    cases = (({}, dict(sweep=14, os=-79.0, rr=5.0, longs_only=True)),
             ({"Longs Only Mode": False, "Sweep Lookback (bars)": 8, "Risk to Reward Ratio": 2.0, "%R Oversold Level": -70.0}, dict(sweep=8, os=-70.0, rr=2.0, longs_only=False)))
    for params, ov in cases:
        ok, m = one(df, params, ov)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
