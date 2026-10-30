"""Independent check — Strict 1-Trade/Day SMC v13 (AeYVHi9k): 5-minute bars (24 h synthetic, drift-free, price ~100) of a stock-style symbol, 10 shares per entry (the 10 %-of-equity sizing replaced), market orders at the next open, commission / slippage off.
Sessions at a fixed UTC-5 offset (opening range 09:30-09:45, regular 09:30-16:00, entry cutoff 12:00-16:00, exit 14:00-16:00), the D-period reset of the opening range and the trade counter (09:30 New York periods), 2-bar swing change of character within 5 bars, fair-value gap, one trade a day, the entry with a trailing stop (activation at the signal close, offset 3 ATR(15) in ticks) and a 2 x range target, the 1R / SMA-cross half close, the 3-hour break-even stop and the exit-window close_all are restated bar by bar.
Uses the quantity-aware bracket reference (indep.simulate_brackets with trailing legs). Variants: defaults; ATR multiplier 1.5 with a 12:00 .. 13:00 UTC-5 entry window."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_cross_over, np_cross_under, np_periods, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "AeYVHi9k"


def pivots(x, left, right, high):
    out = np.full(len(x), False)
    for i in range(left + right, len(x)):
        w = x[i - left - right:i + 1]
        ctr = w[left]
        a, b = w[:left], w[left + 1:]
        out[i] = ((a < ctr).all() and (b <= ctr).all()) if high else ((a > ctr).all() and (b >= ctr).all())
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
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    t = df["time"].to_numpy()
    mins = (((pd.to_datetime(df["time"], unit="ms", utc=True) - pd.Timedelta(hours=5)).dt.hour * 60) + (pd.to_datetime(df["time"], unit="ms", utc=True) - pd.Timedelta(hours=5)).dt.minute).to_numpy()
    in_orb = (mins >= 570) & (mins < 585)
    rth = (mins >= 570) & (mins < 960)
    cutoff = (mins >= p["cut0"]) & (mins < 960)
    exitw = (mins >= 840) & (mins < 960)
    pid, _ = np_periods(df, 1440)
    ph, pl = pivots(h, 2, 2, True), pivots(l, 2, 2, False)
    atr = np_atr(h, l, c, 15)
    sf, ss = np_sma(c, 10), np_sma(c, 20)
    cu_ma, co_ma = np_cross_under(sf, ss), np_cross_over(sf, ss)
    S = dict(orh=np.nan, orl=np.nan, lsh=np.nan, lsl=np.nan, tc=0, ep=np.nan, p1=False, be=False, bu=[], bd=[], prev_sh=np.nan, prev_sl=np.nan, lu=None, ld=None)

    def orders(i, info):
        out = []
        pos = info["pos"]
        new_day = i > 0 and pid[i] != pid[i - 1]
        if new_day:
            S["orh"] = S["orl"] = np.nan
        elif in_orb[i]:
            S["orh"] = h[i] if np.isnan(S["orh"]) else max(S["orh"], h[i])
            S["orl"] = l[i] if np.isnan(S["orl"]) else min(S["orl"], l[i])
        if ph[i]:
            S["lsh"] = h[i - 2]
        if pl[i]:
            S["lsl"] = l[i - 2]
        with np.errstate(invalid="ignore"):
            h2, l2 = (h[i - 2], l[i - 2]) if i >= 2 else (np.nan, np.nan)
            bf, sf_ = l[i] > h2, h[i] < l2
            after = (not in_orb[i]) and (not np.isnan(S["orh"])) and rth[i]
            before = not cutoff[i]
            # ta.crossover(close, lastSwingHigh): close > level now and close[1] <= level[1]
            cx_up = bool(i > 0 and c[i] > S["lsh"] and c[i - 1] <= S["prev_sh"])
            cx_dn = bool(i > 0 and c[i] < S["lsl"] and c[i - 1] >= S["prev_sl"])
        S["prev_sh"], S["prev_sl"] = S["lsh"], S["lsl"]
        if cx_up:
            S["lu"] = i
        if cx_dn:
            S["ld"] = i
        bs_u = i - S["lu"] if S["lu"] is not None else np.nan
        bs_d = i - S["ld"] if S["ld"] is not None else np.nan
        if new_day:
            S["tc"] = 0
        rng = S["orh"] - S["orl"]
        can = after and before and pos == 0 and S["tc"] == 0
        a = atr[i]
        with np.errstate(invalid="ignore"):
            lc = bool(can and c[i] > S["orh"] and bs_u <= 5 and bf)
            sc = bool(can and c[i] < S["orl"] and bs_d <= 5 and sf_)
        off = a * p["mult"] / 0.01
        if lc:
            S["ep"] = c[i]
            out += [("entry", "Long", 1, 10.0), ("exit", "Exit Long", "Long", None, None, S["ep"] + rng * 2, None, S["ep"], off)]
            S["tc"], S["p1"], S["be"] = 1, False, False
        if sc:
            S["ep"] = c[i]
            out += [("entry", "Short", -1, 10.0), ("exit", "Exit Short", "Short", None, None, S["ep"] - rng * 2, None, S["ep"], off)]
            S["tc"], S["p1"], S["be"] = 1, False, False
        if pos != 0:
            if not S["p1"]:
                hit = (pos > 0 and h[i] >= S["ep"] + rng) or (pos < 0 and l[i] <= S["ep"] - rng)
                cross = (pos > 0 and cu_ma[i]) or (pos < 0 and co_ma[i])
                if hit or cross:
                    out += [("close", "Long", 50.0), ("close", "Short", 50.0)]
                    S["p1"] = True
            if not S["be"] and info["lots"]:
                if t[i] - 0 > 0 and (t[i] - _entry_time(info)) > 10800000:
                    out.append(("exit", "BE Long" if pos > 0 else "BE Short", "Long" if pos > 0 else "Short", None, S["ep"], None))
                    S["be"] = True
        if exitw[i]:
            out.append(("close_all",))
        return out

    def _entry_time(info):
        return t[info["lots"][-1]["eb"]]

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=0.01, qty_step=1e-9)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": 10.0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


def check():
    df = bars(60000, seed=5, freq="5min")
    lc = np.log(df["close"].to_numpy() / 100)
    det = lc - np.polyval(np.polyfit(np.arange(len(lc)), lc, 1), np.arange(len(lc)))
    rel = {k: df[k].to_numpy() / df["close"].to_numpy() for k in ("open", "high", "low", "close")}
    for k in rel:
        df[k] = 100 * np.exp(0.4 * det) * rel[k] ** 0.4
    msgs, allok = [], True
    cases = (({}, dict(mult=3.0, cut0=720)),
             ({"ATR Multiplier": 1.5, "Entry Cutoff Session": "1300-1600"}, dict(mult=1.5, cut0=780)))
    for params, ov in cases:
        ok, m = one(df, params, ov)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
