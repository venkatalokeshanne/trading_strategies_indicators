"""Independent check — ORB PRO + FILTERS (iVhgGLYt): 15-minute bars (24 h synthetic) on a crypto-style symbol (UTC exchange time), market orders at the next open, default quantity 1, commission / slippage / margin off.
Opening range = high / low of the bars with UTC hour in [start, end), cleared at each UTC midnight; the session is 14:00 - 23:00 Amsterdam time of the bar's UTC calendar date. Entry: close crossing the range edge from the inside (previous close at or inside it) in the session, outside the range window, on the right side of the 50 EMA; opposite entry reverses.
While in a position, every bar re-issues the exit orders from the position's average entry price: take-profit (50 % of the entry quantity) at entry +/- the distance to the stop (stop = the other side of the range), and a runner (the rest) with that stop. The runner's trailing arguments carry no offset, so no trailing stop is active;
a range that is not yet defined (nan) leaves the exit order without a stop or limit. Uses the quantity-aware bracket reference (indep.simulate_brackets), which also compares the closed quantities.
Variants: defaults; ORB hours 6-9 with a 20-bar ATR; ORB hours 9-10."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_ema, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "iVhgGLYt"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    t = pd.to_datetime(df["time"], unit="ms", utc=True)
    hour = t.dt.hour.to_numpy()
    day = t.dt.normalize()
    new_day = np.r_[False, (day.to_numpy()[1:] != day.to_numpy()[:-1])]
    ams = lambda hh: np.array([pd.Timestamp(year=d.year, month=d.month, day=d.day, hour=hh, tz="Europe/Amsterdam").value // 1_000_000 for d in day], dtype=np.int64)
    s0, s1 = ams(14), ams(23)
    tm = df["time"].to_numpy()
    in_sess = (tm >= s0) & (tm <= s1)
    ema = np_ema(c, 50)
    atr = np_atr(h, l, c, p["atrl"])
    S = dict(hi=np.nan, lo=np.nan)
    sym = SymbolInfo.make("BINANCE:XYZUSDT", "crypto", qty_step=1e-9)

    def orders(i, info):
        in_orb = p["s"] <= hour[i] < p["e"]
        if in_orb:
            S["hi"] = h[i] if np.isnan(S["hi"]) else max(S["hi"], h[i])
            S["lo"] = l[i] if np.isnan(S["lo"]) else min(S["lo"], l[i])
        if new_day[i]:
            S["hi"] = S["lo"] = np.nan
        hi, lo = S["hi"], S["lo"]
        out = []
        with np.errstate(invalid="ignore"):
            lc = c[i] > hi and i > 0 and c[i - 1] <= hi and in_sess[i] and not in_orb and c[i] > ema[i]
            sc = c[i] < lo and i > 0 and c[i - 1] >= lo and in_sess[i] and not in_orb and c[i] < ema[i]
        if lc:
            out.append(("entry", "BUY", 1, 1.0))
        if sc:
            out.append(("entry", "SELL", -1, 1.0))
        pos, avg = info["pos"], info["avg"]
        if pos > 0:
            tp = avg + (avg - lo)
            out += [("exit", "TP BUY", "BUY", 50, None, None if np.isnan(tp) else tp), ("exit", "RUNNER BUY", "BUY", None, None if np.isnan(lo) else lo, None)]
        if pos < 0:
            tp = avg - (hi - avg)
            out += [("exit", "TP SELL", "SELL", 50, None, None if np.isnan(tp) else tp), ("exit", "RUNNER SELL", "SELL", None, None if np.isnan(hi) else hi, None)]
        return out

    ref = simulate_brackets(o, h, l, c, orders, tick=sym.mintick)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(s=7, e=8, atrl=14)


def check():
    df = bars(30000, seed=81, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    cases = (({}, {}),
             ({"ORB Start": 6, "ORB End": 9, "ATR Length": 20}, dict(s=6, e=9, atrl=20)),
             ({"ORB Start": 9, "ORB End": 10}, dict(s=9, e=10)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
