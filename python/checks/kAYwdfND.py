"""Independent check — Simplified 30m Event Strategy - Reverse (kAYwdfND): 5-minute bars (24 h synthetic, price ~1000) on a crypto-style symbol (30-minute periods from UTC midnight), market orders at the next open, fixed quantity 10 on the pinelib side, commission / slippage / margin off.
The 30-minute high / low (period extremes, lookahead off: a period's value shows on its last chart bar, the previous period's before that) form a staircase on the chart; pivots on that staircase use left bars strictly lower and right bars not higher (high side; mirrored for lows) over chart bars. The latest pivot values persist (valuewhen);
valid = both known and their gap >= the minimum; long = valid, close over the last pivot low, volume delta < 0 (delta = +volume on an up candle, -volume on a down candle); short = valid, close under the last pivot high, delta > 0. A side's bar counter counts bars with that position open at script time; at the exit count the side is closed at the next open;
entries after the closes in source order; pyramiding 1. Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too.
Variants: defaults; pivots 1 / 2, exit after 3 bars; minimum range 2 and exit after 12 bars."""
import numpy as np

from indep import bars, compare_q, np_periods, np_security_lookahead_off, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "kAYwdfND"
QTY = 10.0


def pivot_high(x, left, right):
    n = len(x)
    out = np.full(n, np.nan)
    for i in range(left + right, n):
        m = i - right
        c = x[m]
        if np.isnan(c):
            continue
        lw, rw = x[m - left:m], x[m + 1:i + 1]
        if np.all(c > lw) and np.all(c >= rw):
            out[i] = c
    return out


def pivot_low(x, left, right):
    n = len(x)
    out = np.full(n, np.nan)
    for i in range(left + right, n):
        m = i - right
        c = x[m]
        if np.isnan(c):
            continue
        lw, rw = x[m - left:m], x[m + 1:i + 1]
        if np.all(c < lw) and np.all(c <= rw):
            out[i] = c
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    pid, last_of = np_periods(df, 30, start_minutes=0, tz="UTC")
    nper = int(pid.max()) + 1
    ph_per = np.full(nper, -np.inf)
    pl_per = np.full(nper, np.inf)
    for i in range(n):
        ph_per[pid[i]] = max(ph_per[pid[i]], h[i])
        pl_per[pid[i]] = min(pl_per[pid[i]], l[i])
    h30 = np_security_lookahead_off(ph_per, pid, last_of)
    l30 = np_security_lookahead_off(pl_per, pid, last_of)
    pH, pL = pivot_high(h30, p["l"], p["r"]), pivot_low(l30, p["l"], p["r"])
    S = dict(ph=np.nan, pl=np.nan, lc=0, sc=0)

    def orders(i, info):
        out = []
        if not np.isnan(pH[i]):
            S["ph"] = pH[i]
        if not np.isnan(pL[i]):
            S["pl"] = pL[i]
        pos = info["pos"]
        with np.errstate(invalid="ignore"):
            valid = (not np.isnan(S["ph"])) and (not np.isnan(S["pl"])) and (S["ph"] - S["pl"]) >= p["mr"]
            delta = v[i] if c[i] > o[i] else (-v[i] if c[i] < o[i] else 0.0)
            ls = valid and c[i] > S["pl"] and delta < 0
            ss = valid and c[i] < S["ph"] and delta > 0
        S["lc"] = S["lc"] + 1 if pos > 0 else 0
        S["sc"] = S["sc"] + 1 if pos < 0 else 0
        if S["lc"] >= p["x"]:
            out.append(("close", "Long"))
        if S["sc"] >= p["x"]:
            out.append(("close", "Short"))
        if ls:
            out.append(("entry", "Long", 1, QTY))
        if ss:
            out.append(("entry", "Short", -1, QTY))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1)
    sym = SymbolInfo.make("BINANCE:XYZUSDT", "crypto", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(l=2, r=3, x=6, mr=5.0)


def check():
    df = bars(30000, seed=231, freq="5min")
    base = df["close"].iloc[0]
    for k in ("open", "high", "low", "close"):
        df[k] = 1000 * (df[k] / base) ** 0.15
    msgs, allok = [], True
    cases = (({"Min Pivot Range": 1.0}, dict(mr=1.0)),
             ({"Pivot Left": 1, "Pivot Right": 2, "Exit after X bars (5min)": 3, "Min Pivot Range": 1.0}, dict(l=1, r=2, x=3, mr=1.0)),
             ({"Min Pivot Range": 2.0, "Exit after X bars (5min)": 12}, dict(mr=2.0, x=12)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
