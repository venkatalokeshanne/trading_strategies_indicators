"""Independent check — Beginner Trend & Risk (BjjAOuub): hourly bars on a mean-reverting synthetic price around 100 (OU), so the 1 %-of-equity risk size floor(equity * 1 % / ATR) stays >= 1 and the entry is never skipped
(quantity itself does not move prices). Long only: EMA9 crossing over EMA21 with 30 < RSI14 < 70 enters when not long; entry + exit (stop 1 ATR, limit 2 ATR from the signal close) are issued on the signal bar, so the
bracket works from the fill bar. EMA cross under or RSI14 > 70 while long closes at the next open. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import compare, np_atr, np_cross_over, np_cross_under, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "BjjAOuub"


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
    df = ou_bars(30000, 269, 100.0, 0.01, 1.0, "1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    f, s, rsi, atr = np_ema(c, 9), np_ema(c, 21), np_rsi(c, 14), np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        en = np_cross_over(f, s) & (f > s) & (rsi > 30) & (rsi < 70)
        ex = np_cross_under(f, s) | (rsi > 70)
    lvl = [np.nan, np.nan]

    def orders(i, pos):
        out = []
        if en[i] and pos <= 0:
            out.append(("entry", 1)); lvl[0], lvl[1] = c[i] - atr[i], c[i] + atr[i] * 2.0
        if ex[i] and pos > 0:
            out.append(("close", 1))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: lvl[0], target=lambda i, pos, ep, eb: lvl[1])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
