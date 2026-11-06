"""Independent check — Ema Cross + imb KOCHAN STYLE (NA6e6cHO): 5-minute bars (24 h synthetic, price ~100, mintick 0.01) of a crypto-style symbol, default quantity 1, margin / commission / slippage off.
Everything comes from the previous bar: trend (EMA fast[1] over EMA slow[1] and close[1] over EMA fast[1]), fair-value gap (low[1] over high[3] by at least the minimum ticks), imbalance candle (close[1] over open[1], body over 65 % of the range, volume[1] over its 20-bar SMA[1]) and a break of high[2]; mirrored for shorts.
Between 07:30 and 10:00 at UTC-6 while flat, a pending buy-stop (sell-stop) buffer ticks beyond the signal close is placed (replaced by the next signal, never cancelled) together with an exit order (stop = signal close +/- buffer ticks -/+ stop points, trailing stop with activation = break-even points / tick and offset = trail points / tick) that waits for its entry.
Uses the quantity-aware bracket reference (indep.simulate_brackets: stop entries, trailing leg), comparing quantities too.
Variants: defaults; wider stop / trail and a zero-tick gap; buffer 3 ticks, tighter break-even."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_ema, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "NA6e6cHO"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    sym = SymbolInfo.make("BINANCE:XYZUSDT", "crypto", qty_step=1e-9)
    tick = sym.mintick
    loc = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Etc/GMT+6")
    hhmm = (loc.dt.hour * 100 + loc.dt.minute).to_numpy()
    ef, es, av = np_ema(c, 9), np_ema(c, 21), np_sma(v, 20)

    def orders(i, info):
        if i < 3:
            return []
        out = []
        rng = h[i - 1] - l[i - 1]
        body = abs(c[i - 1] - o[i - 1])
        ratio = body / rng if rng != 0 else np.nan
        with np.errstate(invalid="ignore"):
            tu = ef[i - 1] > es[i - 1] and c[i - 1] > ef[i - 1]
            td = ef[i - 1] < es[i - 1] and c[i - 1] < ef[i - 1]
            bg = max(l[i - 1] - h[i - 3], 0.0)
            sg = max(l[i - 3] - h[i - 1], 0.0)
            bi = c[i - 1] > o[i - 1] and ratio > 0.65 and v[i - 1] > av[i - 1]
            si = c[i - 1] < o[i - 1] and ratio > 0.65 and v[i - 1] > av[i - 1]
            ol = tu and l[i - 1] > h[i - 3] and bg / tick >= p["gap"] and bi and h[i - 1] > h[i - 2]
            osh = td and h[i - 1] < l[i - 3] and sg / tick >= p["gap"] and si and l[i - 1] < l[i - 2]
        ok = 730 <= hhmm[i] <= 1000 and info["pos"] == 0
        tp, to = p["be"] / tick, p["trail"] / tick
        if ol and ok:
            out += [("entry", "Long Entry", 1, 1.0, c[i] + p["buf"] * tick, None),
                    ("exit", "Long Exit", "Long Entry", None, c[i] + p["buf"] * tick - p["sl"], None, tp, None, to)]
        if osh and ok:
            out += [("entry", "Short Entry", -1, 1.0, c[i] - p["buf"] * tick, None),
                    ("exit", "Short Exit", "Short Entry", None, c[i] + p["buf"] * tick + p["sl"], None, tp, None, to)]
        return out

    ref = simulate_brackets(o, h, l, c, orders, tick=tick)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(gap=2, sl=5, be=3, trail=5, buf=1)


def check():
    df = bars(60000, seed=211, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.25
    msgs, allok = [], True
    cases = (({"Min FVG tol in ticks": 0}, dict(gap=0)),
             ({"Min FVG tol in ticks": 0, "Stop loss points": 2, "Trail by x points": 1, "Breakeven at x points": 1}, dict(gap=0, sl=2, trail=1, be=1)),
             ({"Min FVG tol in ticks": 0, "Buffer ticks on stop order": 3, "Breakeven at x points": 0}, dict(gap=0, buf=3, be=0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
