"""Independent check — Pivot VWAP Strategy with target pivots (UtsDI4uZ): 5-minute bars (24 h synthetic, drift-free, price ~100) of a stock-style symbol, market orders at the next open, fixed quantity (the 100 %-of-equity sizing replaced), commission / slippage off.
Eleven daily pivot levels from the previous D period's high / low / close (D periods start at 09:30 New York, lookahead on), the manual regular-session VWAP restarting at the first regular bar of each period, the 09:30-14:00 window, the 2-signals-a-day counter keyed on the day of the month, the poke-through-and-close-back entries (level AND VWAP), and the two-closes-through-VWAP exits are restated bar by bar.
Uses the quantity-aware bracket reference (indep.simulate_brackets). Variants: two different series."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_periods, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "UtsDI4uZ"
QTY = 10.0


def make(seed, pw=0.12):
    df = bars(30000, seed=seed, freq="5min")
    lc = np.log(df["close"].to_numpy() / 100)
    det = lc - np.polyval(np.polyfit(np.arange(len(lc)), lc, 1), np.arange(len(lc)))
    rel = {k: df[k].to_numpy() / df["close"].to_numpy() for k in ("open", "high", "low", "close")}
    for k in rel:
        df[k] = 100 * np.exp(pw * det) * rel[k] ** pw
    return df


def one(df):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    loc = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (loc.dt.hour * 60 + loc.dt.minute).to_numpy()
    dom = loc.dt.day.to_numpy()
    mkt = (mins >= 570) & (mins < 960)
    intime = (mins >= 570) & (mins < 840)
    pid, _ = np_periods(df, 1440)
    g = pd.DataFrame({"pid": pid, "h": h, "l": l, "c": c}).groupby("pid")
    ph, pl, pc = g["h"].max().to_numpy(), g["l"].min().to_numpy(), g["c"].last().to_numpy()
    prev = lambda a: np.array([a[pid[i] - 1] if pid[i] > 0 else np.nan for i in range(n)])
    PH, PL, PC = prev(ph), prev(pl), prev(pc)
    P = (PH + PL + PC) / 3
    R1, R2, R3 = 2 * P - PL, P + (PH - PL), PH + 2 * (P - PL)
    S1, S2, S3 = 2 * P - PH, P - (PH - PL), PL - 2 * (PH - P)
    rng = R1 - S1
    R4, S4 = R3 + rng, S3 - rng
    R5, S5 = R4 + rng, S4 - rng
    levels = [P, R1, R2, R3, R4, R5, S1, S2, S3, S4, S5]
    tp = (h + l + c) / 3
    S = dict(num=0.0, den=0.0, sig=0, last_day=0, tl=np.nan, ts=np.nan)

    def next_above(price, i):
        r = R5[i]
        for lv in levels:
            if lv[i] > price and lv[i] < r:
                r = lv[i]
        return r

    def next_below(price, i):
        r = S5[i]
        for lv in levels:
            if lv[i] < price and lv[i] > r:
                r = lv[i]
        return r

    def orders(i, info):
        out = []
        pos = info["pos"]
        new_session = i > 0 and pid[i] != pid[i - 1] and mkt[i]
        if new_session:
            S["num"] = S["den"] = 0.0
        if mkt[i]:
            S["num"] += tp[i] * v[i]
            S["den"] += v[i]
        vw = S["num"] / S["den"] if S["den"] > 0 else np.nan
        if dom[i] != S["last_day"]:
            S["sig"] = 0
        can = intime[i] and S["sig"] < 2
        c1 = c[i - 1] if i else np.nan
        with np.errstate(invalid="ignore"):
            ok = can and not np.isnan(vw)
            lg = ok and any((l[i] < lv[i] and l[i] < vw and c[i] > lv[i] and c[i] > vw) or (c[i] > lv[i] and c[i] > vw and c1 < lv[i] and c1 < vw) for lv in levels)
            sh = ok and any((h[i] > lv[i] and h[i] > vw and c[i] < lv[i] and c[i] < vw) or (c[i] < lv[i] and c[i] < vw and c1 > lv[i] and c1 > vw) for lv in levels)
        if lg and pos == 0:
            out.append(("entry", "Long", 1, QTY))
            S["tl"] = next_above(c[i], i)
            S["sig"] += 1
            S["last_day"] = dom[i]
        if sh and pos == 0:
            out.append(("entry", "Short", -1, QTY))
            S["ts"] = next_below(c[i], i)
            S["sig"] += 1
            S["last_day"] = dom[i]
        with np.errstate(invalid="ignore"):
            if pos > 0:
                if (not np.isnan(S["tl"])) and h[i] >= S["tl"] and c[i] < S["tl"]:
                    out.append(("close", "Long"))
                    S["tl"] = np.nan
                elif (not np.isnan(vw)) and c[i] < vw:
                    out.append(("close", "Long"))
                    S["tl"] = np.nan
            if pos < 0:
                if (not np.isnan(S["ts"])) and l[i] <= S["ts"] and c[i] > S["ts"]:
                    out.append(("close", "Short"))
                    S["ts"] = np.nan
                elif (not np.isnan(vw)) and c[i] > vw:
                    out.append(("close", "Short"))
                    S["ts"] = np.nan
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=0.01, qty_step=1e-9)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


def check():
    msgs, allok = [], True
    for seed in (151, 152):
        ok, m = one(make(seed))
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
