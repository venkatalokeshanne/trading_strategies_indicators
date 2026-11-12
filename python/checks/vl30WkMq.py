"""Independent check — ADR AsianLS (vl30WkMq): 15-minute bars (24 h synthetic, price ~2000) of a crypto-style symbol, entry quantity 2 (exits of 1 each), commission / slippage / margin off.
Asia session = bar open time 19:00 - 24:00 at GMT-3 (high / low tracked from the session's first bar, one trade allowed per cycle), operating window 00:00 - 12:00 GMT-3 outside the session. Buy: close over the session high on an up candle whose body is at least the threshold % of its range (sell mirrored under the session low).
Exit orders issued with the entry: TP1 (1 contract) limit at +10 points with the stop 10 points inside the session extreme; runner (1 contract) with the same stop and a trailing stop (activation 10 ticks, offset 5 ticks). Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too.
Variants: defaults; body threshold 40 %; threshold 80 %."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "vl30WkMq"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sym = SymbolInfo.make("BINANCE:XYZUSDT", "crypto", qty_step=1e-9)
    tick = sym.mintick
    loc = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Etc/GMT+3")
    mins = (loc.dt.hour * 60 + loc.dt.minute).to_numpy()
    asia = mins >= 19 * 60
    win = mins < 12 * 60
    S = dict(hi=np.nan, lo=np.nan, td=0, prev=False)

    def orders(i, info):
        out = []
        ins = bool(asia[i])
        new = ins and not S["prev"]
        S["prev"] = ins
        if new:
            S.update(hi=h[i], lo=l[i], td=0)
        elif ins:
            S["hi"], S["lo"] = max(S["hi"], h[i]), min(S["lo"], l[i])
        rng, body = h[i] - l[i], abs(c[i] - o[i])
        strong = body / (rng if rng > 0 else 1) * 100 >= p["bt"]
        can = (not ins) and win[i] and S["td"] < 1
        with np.errstate(invalid="ignore"):
            lc = can and c[i] > S["hi"] and o[i] < c[i] and strong
            sc = can and c[i] < S["lo"] and o[i] > c[i] and strong
        if lc:
            S["td"] = 1
            sl = S["hi"] - 10.0
            out += [("entry", "Buy", 1, 2.0), ("exit", "TP1-Buy", "Buy", ("qty", 1.0), sl, c[i] + 10.0),
                    ("exit", "TP2-Trail-Buy", "Buy", ("qty", 1.0), sl, None, 10.0, None, 5.0)]
        if sc:
            S["td"] = 1
            sl = S["lo"] + 10.0
            out += [("entry", "Sell", -1, 2.0), ("exit", "TP1-Sell", "Sell", ("qty", 1.0), sl, c[i] - 10.0),
                    ("exit", "TP2-Trail-Sell", "Sell", ("qty", 1.0), sl, None, 10.0, None, 5.0)]
        return out

    ref = simulate_brackets(o, h, l, c, orders, tick=tick)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(bt=65.0)


def check():
    df = bars(30000, seed=291, freq="15min")
    base = df["close"].iloc[0]
    for k in ("open", "high", "low", "close"):
        df[k] = 2000 * (df[k] / base) ** 0.1
    msgs, allok = [], True
    cases = (({}, {}), ({"% Mínimo de Cuerpo (Sugerido)": 40.0}, dict(bt=40.0)), ({"% Mínimo de Cuerpo (Sugerido)": 80.0}, dict(bt=80.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
