"""Independent check — Sniper V4 (72gQqAzW): hourly bars. Bull exhaustion = RSI14 < 35, volume > 1.2 * SMA20 and (low < previous low or a sweep: low < the lowest low of the 20 bars before this one with the close back above it); bear mirrored.
Exhaustion arms a window of 12 bars (bar_index - last <= 12 and last != 0); in it the close crossing over the previous high with RSI rising buys when flat (mirror: short). A fill resets that side's marker to 0. The opposite
exhaustion closes an open position at the next open. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import compare, np_cross_over, np_cross_under, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "72gQqAzW"


def ou_bars(n, seed, mu, theta, sigma, freq):
    rng = np.random.default_rng(seed)
    x = np.empty(n)
    x[0] = mu
    for i in range(1, n):
        x[i] = x[i - 1] + theta * (mu - x[i - 1]) + sigma * rng.normal()
    open_ = np.r_[x[0], x[:-1]] + rng.normal(0, sigma / 8, n)
    high = np.maximum(open_, x) + np.abs(rng.normal(0, sigma / 2, n))
    low = np.minimum(open_, x) - np.abs(rng.normal(0, sigma / 2, n))
    t = pd.date_range("2015-01-01", periods=n, freq=freq, tz="UTC").as_unit("ms").asi8
    return pd.DataFrame({"time": t, "open": open_, "high": high, "low": low, "close": x, "volume": rng.integers(1000, 100000, n).astype(float)})


def check():
    # mean-reverting price (OU around 100): with 100 % of equity per trade a trending synthetic series would take equity negative and stop all fills
    df = ou_bars(30000, 297, 100.0, 0.01, 1.0, "1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    rsi, vm = np_rsi(c, 14), np_sma(v, 20)
    ph = pd.Series(h).shift(1).rolling(20).max().to_numpy()
    pl = pd.Series(l).shift(1).rolling(20).min().to_numpy()
    h1, l1, r1 = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]], np.r_[np.nan, rsi[:-1]]
    with np.errstate(invalid="ignore"):
        bgrab, sgrab = (l < pl) & (c > pl), (h > ph) & (c < ph)
        bex = (rsi < 35) & (v > vm * 1.2) & ((l < l1) | bgrab)
        sex = (rsi > 65) & (v > vm * 1.2) & ((h > h1) | sgrab)
        xu, xd = np_cross_over(c, h1), np_cross_under(c, l1)
        rising, falling = rsi > r1, rsi < r1
    st = dict(lb=0, ls=0)

    def orders(i, pos):
        if bex[i]:
            st["lb"] = i
        if sex[i]:
            st["ls"] = i
        bact = (i - st["lb"] <= 12) and st["lb"] != 0
        sact = (i - st["ls"] <= 12) and st["ls"] != 0
        out = []
        if bact and xu[i] and rising[i] and pos == 0:
            out.append(("entry", 1)); st["lb"] = 0
        if sact and xd[i] and falling[i] and pos == 0:
            out.append(("entry", -1)); st["ls"] = 0
        if sex[i] and pos > 0:
            out.append(("close", 1))
        if bex[i] and pos < 0:
            out.append(("close", -1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
