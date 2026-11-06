"""Independent check — MNQ Prop Firm Execution System (qmvY3luY): 5-minute bars (24 h synthetic, price ~100) of a stock-style symbol with a point value of 500 (so the +150 / -300 daily thresholds are reachable), market orders at the next open, commission / slippage off.
3-bar pivots keep the last swing high / low; a sweep (low under the swing low and close back above it, or the mirror) with the 200 EMA side, the 13:00-16:00 New York session and the daily risk engine (3 counted signals, equity change since the day's first bar > -300; the day changes at 09:30 New York) triggers an entry of 1 contract (2 above +150 today) with a half-size 1 : 1 target and a runner with a 1.8 : 1 target and the swing stop. The counter ticks on every signal, also for entries ignored by pyramiding 0.
Uses the quantity-aware bracket reference (indep.simulate_brackets), the equity (initial capital + closed P&L x point value + open P&L) mirrored for the daily engine. Variants: 5-minute and 15-minute bars."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_ema, np_periods, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "qmvY3luY"
PV = 500.0


def pivots(x, left, right, high):
    out = np.full(len(x), False)
    for i in range(left + right, len(x)):
        w = x[i - left - right:i + 1]
        ctr = w[left]
        a, b = w[:left], w[left + 1:]
        out[i] = ((a < ctr).all() and (b <= ctr).all()) if high else ((a > ctr).all() and (b >= ctr).all())
    return out


def one(df, tf):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    loc = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (loc.dt.hour * 60 + loc.dt.minute).to_numpy()
    sess = (mins >= 13 * 60) & (mins < 16 * 60)
    ema = np_ema(c, 200)
    ph, pl = pivots(h, 3, 3, True), pivots(l, 3, 3, False)
    pid, _ = np_periods(df, 1440)
    S = dict(sh=np.nan, sl=np.nan, es=None, tr=0)
    log: list = []

    def equity(info, i):
        return 1_000_000.0 + PV * (sum(d * (xp - ep) * q for d, _, ep, _, xp, q in log) + sum(x["d"] * x["q"] * (c[i] - x["ep"]) for x in info["lots"]))

    def orders(i, info):
        out = []
        if ph[i]:
            S["sh"] = h[i - 3]
        if pl[i]:
            S["sl"] = l[i - 3]
        eq = equity(info, i)
        if i == 0:
            S["es"] = eq
        if i > 0 and pid[i] != pid[i - 1]:
            S["es"], S["tr"] = eq, 0
        dpnl = eq - S["es"]
        can = S["tr"] < 3 and dpnl > -300
        with np.errstate(invalid="ignore"):
            sw_l = (not np.isnan(S["sl"])) and l[i] < S["sl"] and c[i] > S["sl"]
            sw_h = (not np.isnan(S["sh"])) and h[i] > S["sh"] and c[i] < S["sh"]
            up, dn = c[i] > ema[i], c[i] < ema[i]
        qty = 2.0 if dpnl > 150 else 1.0
        if sess[i] and can and sw_l and up:
            sl = S["sl"]
            out += [("entry", "BUY", 1, qty), ("exit", "BUY TP1", "BUY", 50.0, None, c[i] + (c[i] - sl)), ("exit", "BUY TP2", "BUY", None, sl, c[i] + (c[i] - sl) * 1.8)]
            S["tr"] += 1
        if sess[i] and can and sw_h and dn:
            sl = S["sh"]
            out += [("entry", "SELL", -1, qty), ("exit", "SELL TP1", "SELL", 50.0, None, c[i] - (sl - c[i])), ("exit", "SELL TP2", "SELL", None, sl, c[i] - (sl - c[i]) * 1.8)]
            S["tr"] += 1
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=0.01, qty_step=1e-9, log=log)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9, pointvalue=PV)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf=tf, strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


def check():
    msgs, allok = [], True
    for freq, tf, seed in (("5min", "5", 81), ("15min", "15", 82)):
        df = bars(40000, seed=seed, freq=freq)
        for k in ("open", "high", "low", "close"):
            df[k] = 100 * (df[k] / 100) ** 0.15
        ok, m = one(df, tf)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
