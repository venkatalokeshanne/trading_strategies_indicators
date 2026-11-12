"""Independent check — MNQ StochRSI Long & Short (9u8pzF0I): 2-minute bars (24 h synthetic, MNQ-style price ~15000, 0.25 tick) on a CME futures symbol, market orders at the next open, 8 contracts, commission / slippage / margin off.
K = SMA3 of the stochastic of the RSI (the smoothing is summed like the engine's rolling sum: saturated stochastic values create exact ties). Armed / EMA-touched / entry flags per side exactly as the source (flags move only while flat and outside the 16:58 - 18:00 New York dead zone); the 16:58 bar saves the direction and closes, the 18:00 bar re-opens it.
Every bar both sides re-issue an exit order: hard stop (avg price -/+ dollar stop / dollars per point; none while flat) and a trailing stop with activation = offset = the trail input in ticks; a K reaching the exit level closes at the next open.
Uses the quantity-aware bracket reference (indep.simulate_brackets), which also compares the closed quantities.
Variants: loose levels (arm 80 / 20, entry 60 / 40, exits 20 / 80) with defaults for the rest; a tight dollar stop and short trails."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_ema, np_rsi, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "9u8pzF0I"


def sma_prefix(x, n):
    out = np.full(len(x), np.nan)
    psum = [0.0]
    pnan = [0]
    for i, v in enumerate(x):
        m = i
        if m + 1 >= n and not np.isnan(v) and pnan[m] - pnan[m - (n - 1)] == 0:
            out[i] = (psum[m] - psum[m - (n - 1)] + v) / n
        psum.append(psum[-1] + (0.0 if np.isnan(v) else v))
        pnan.append(pnan[-1] + (1 if np.isnan(v) else 0))
    return out


def stoch_na(src, n):
    """ta.stoch(src, src, src, n): highest / lowest ignore na values once n bars exist, a zero range gives na."""
    out = np.full(len(src), np.nan)
    for i in range(n - 1, len(src)):
        w = src[i - n + 1:i + 1]
        w = w[~np.isnan(w)]
        if len(w) and not np.isnan(src[i]) and w.max() != w.min():
            out[i] = 100 * (src[i] - w.min()) / (w.max() - w.min())
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    sym = SymbolInfo.make("CME_MINI:MNQ1!", "futures", mintick=0.25, qty_step=1e-9)
    loc = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (loc.dt.hour * 60 + loc.dt.minute).to_numpy()
    dead = (mins >= 16 * 60 + 58) & (mins < 18 * 60)
    ema = np_ema(c, 20)
    rsi = np_rsi(c, 14)
    K = sma_prefix(stoch_na(rsi, 14), 3)
    hs = p["dollar"] / 16.0
    S = dict(sd=0, sa=False, se=False, la=False, le=False)

    def orders(i, info):
        out = []
        pos, avg = info["pos"], info["avg"]
        k = K[i]
        if mins[i] == 16 * 60 + 58 and pos != 0:
            S["sd"] = 1 if pos > 0 else -1
            out.append(("close_all",))
        if mins[i] == 18 * 60:
            if S["sd"] == 1:
                out.append(("entry", "Long", 1, 8.0))
            elif S["sd"] == -1:
                out.append(("entry", "Short", -1, 8.0))
            S["sd"] = 0
        with np.errstate(invalid="ignore"):
            if pos == 0 and not dead[i]:
                if k >= p["sa"]:
                    S["sa"], S["se"] = True, False
                if k <= p["sx"]:
                    S["sa"], S["se"] = False, False
            if S["sa"] and pos == 0 and not dead[i] and h[i] >= ema[i]:
                S["se"] = True
            if S["sa"] and S["se"] and pos == 0 and k <= p["se_"] and not dead[i]:
                out.append(("entry", "Short", -1, 8.0))
                S["sa"] = S["se"] = False
            if pos == 0 and not dead[i]:
                if k <= p["la"]:
                    S["la"], S["le"] = True, False
                if k >= p["lx"]:
                    S["la"], S["le"] = False, False
            if S["la"] and pos == 0 and not dead[i] and l[i] <= ema[i]:
                S["le"] = True
            if S["la"] and S["le"] and pos == 0 and k >= p["le_"] and not dead[i]:
                out.append(("entry", "Long", 1, 8.0))
                S["la"] = S["le"] = False
        have = pos != 0 and not np.isnan(avg)
        out.append(("exit", "Short Trail Stop", "Short", None, avg + hs if have else None, None, p["st"], None, p["st"]))
        out.append(("exit", "Long Trail Stop", "Long", None, avg - hs if have else None, None, p["lt"], None, p["lt"]))
        with np.errstate(invalid="ignore"):
            if pos < 0 and k <= p["sx"]:
                out.append(("close", "Short"))
            if pos > 0 and k >= p["lx"]:
                out.append(("close", "Long"))
        return out

    ref = simulate_brackets(o, h, l, c, orders, tick=0.25)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="2", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(sa=95.0, se_=75.0, sx=5.0, st=30.0, la=5.0, le_=20.0, lx=95.0, lt=35.0, dollar=3000.0)


def check():
    df = bars(60000, seed=141, freq="2min")
    base = df["close"].iloc[0]
    for k in ("open", "high", "low", "close"):
        df[k] = 15000 * (df[k] / base) ** 0.04
    msgs, allok = [], True
    loose = {"Short Trigger 1 (Arm)": 80.0, "Short Trigger 2 (Entry)": 60.0, "Short Exit (StochRSI)": 20.0, "Long Trigger 1 (Arm)": 20.0, "Long Trigger 2 (Entry)": 40.0, "Long Exit (StochRSI)": 80.0}
    lo = dict(sa=80.0, se_=60.0, sx=20.0, la=20.0, le_=40.0, lx=80.0)
    cases = ((loose, lo),
             ({**loose, "Hard Stop Loss ($)": 400.0, "Short Trailing Stop (points)": 8.0, "Long Trailing Stop (points)": 10.0}, dict(**lo, dollar=400.0, st=8.0, lt=10.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
