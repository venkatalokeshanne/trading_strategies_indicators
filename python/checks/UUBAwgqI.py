"""Independent check — Zach's Quantum Harmonic Oscillator (UUBAwgqI): hourly bars (24 h synthetic) of a stock-style symbol, process_orders_on_close (orders fill at the signal close), quantity 1, commission / slippage / margin off.
Energy = 0.5 x k x z^2 x sign(z), z = (close - SMA(length)) / stdev (population; 1 when the deviation is 0) of the chart-timeframe close. In the regular session (bar open 09:30 - 16:00 New York, Monday - Friday only) energy < -threshold enters long; energy >= 0 closes ('U' ignored when not open at script time).
Uses the quantity-aware bracket reference (indep.simulate_brackets, on_close), comparing quantities too. Variants: defaults with k 4 and threshold 1.5; session filter off, length 10."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "UUBAwgqI"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    wd = ny.dt.dayofweek.to_numpy() < 5
    sess = ((mins >= 570) & (mins < 960) & wd) if p["us"] else np.ones(n, bool)
    L = p["len"]
    sd = np.array([np.std(c[i - L + 1:i + 1]) if i >= L - 1 else np.nan for i in range(n)])
    sm = np.array([np.mean(c[i - L + 1:i + 1]) if i >= L - 1 else np.nan for i in range(n)])
    with np.errstate(invalid="ignore"):
        z = (c - sm) / np.where(sd > 0, sd, 1.0)
        z = np.where(np.isnan(sd), np.nan, z)
        pe = 0.5 * p["k"] * z ** 2 * np.sign(z)

    def orders(i, info):
        out = []
        with np.errstate(invalid="ignore"):
            if pe[i] < -p["ex"] and sess[i]:
                out.append(("entry", "U", 1, 1.0))
            if pe[i] >= 0 and sess[i]:
                out.append(("close", "U"))
        return out

    ref = simulate_brackets(o, h, l, c, orders, on_close=True)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(len=20, k=2.0, ex=2.5, us=True)


def check():
    df = bars(30000, seed=621, freq="1h")
    for kk in ("open", "high", "low", "close"):
        df[kk] = 100 * (df[kk] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({}, {}), ({"Spring Constant (k)": 4.0, "Potential Energy Threshold (U_max)": 1.5}, dict(k=4.0, ex=1.5)),
             ({"Use Session Filter": False, "Lookback Horizon (τ)": 10}, dict(us=False, len=10)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
