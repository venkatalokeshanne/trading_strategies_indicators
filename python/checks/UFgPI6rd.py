"""Independent check — UT Bot Options Seller (UFgPI6rd): 5-min bars. ATR(10)*2 trailing stop ("UT Bot") ratcheting from the previous value (nz -> 0); a close crossing it
with RSI/ADX filters and a candle-spike filter opens a long (cross up, RSI 3-60) or short (cross down, RSI 40-100), only inside 09:15-15:00 Asia/Kolkata on any weekday;
outside that window every position is closed at the next open. math.max/min return na if either operand is na."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_dmi, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "UFgPI6rd"


def nmax(a, b):
    return np.nan if (np.isnan(a) or np.isnan(b)) else max(a, b)


def nmin(a, b):
    return np.nan if (np.isnan(a) or np.isnan(b)) else min(a, b)


def check():
    df = bars(20000, seed=164, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr10, atr14 = np_atr(h, l, c, 10), np_atr(h, l, c, 14)
    loss = 2.0 * atr10
    x = np.full(n, np.nan)
    for i in range(n):
        ps = 0.0 if (i == 0 or np.isnan(x[i - 1])) else x[i - 1]
        pc = c[i - 1] if i else np.nan
        if c[i] > ps and pc > ps:
            x[i] = nmax(ps, c[i] - loss[i])
        elif c[i] < ps and pc < ps:
            x[i] = nmin(ps, c[i] + loss[i])
        elif c[i] > ps:
            x[i] = c[i] - loss[i]
        else:
            x[i] = c[i] + loss[i]
    rsi = np_rsi(c, 14)
    _, _, adx = np_dmi(h, l, c, 14)
    ky = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Asia/Kolkata")
    m = (ky.dt.hour * 60 + ky.dt.minute).to_numpy()
    win = (m >= 555) & (m < 900)
    with np.errstate(invalid="ignore"):
        up, dn = np_cross_over(c, x), np_cross_under(c, x)
        calm = (h - l) <= atr14 * 2.0
        pe = up & (rsi >= 3) & (rsi <= 60) & (adx > 20) & calm
        ce = dn & (rsi >= 40) & (rsi <= 100) & (adx > 20) & calm

    def orders(i, pos):
        out = []
        if win[i]:
            if pe[i]:
                out.append(("entry", 1))
            if ce[i]:
                out.append(("entry", -1))
        elif pos != 0:
            out.append(("close", pos))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
