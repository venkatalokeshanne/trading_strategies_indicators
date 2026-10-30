"""Independent check — Trend Pullback RSI+ATR (AORNVoek): daily bars from 2015, slippage 0, orders at the signal close (process_orders_on_close), long only, bars from 2018-01-01 00:00 UTC on. EMA50 > EMA200 and close > EMA50, RSI14 crossing over 50 with a bar in the last 5 (including the current) where 40 <= RSI <= 50,
ATR14 > 1% of close -> long when flat; stop = close - 2 ATR14, target = close + 4 ATR14 fixed at the signal and issued once the position exists (as of a bar's close), so they work from the bar after that; EMA50 crossing under EMA200 closes the long."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "AORNVoek"


def check():
    df = bars(9000, seed=82)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ef, es, rsi, atr = np_ema(c, 50), np_ema(c, 200), np_rsi(c, 14), np_atr(h, l, c, 14)
    t0 = pd.Timestamp("2018-01-01", tz="UTC").value // 1_000_000
    in_range = df["time"].to_numpy() >= t0
    zone = (rsi <= 50) & (rsi >= 40)
    since = np.full(n, np.nan)
    last = None
    for i in range(n):
        if zone[i]:
            last = i
        since[i] = np.nan if last is None else i - last
    with np.errstate(invalid="ignore"):
        sig = (ef > es) & (c > ef) & (since <= 5) & np_cross_over(rsi, 50.0) & (atr / c * 100 > 1.0) & in_range
    dn = np_cross_under(ef, es)
    lvl = {}
    poscl = np.zeros(n)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if sig[i] and pos == 0:
            out.append(("entry", 1))
            lvl[1] = (c[i] - 2 * atr[i], c[i] + 4 * atr[i])
        if pos > 0 and dn[i]:
            out.append(("close", 1))
        return out

    def stop(i, pos, ep, eb):
        return lvl[1][0] if i > 0 and poscl[i - 1] > 0 else None

    def target(i, pos, ep, eb):
        return lvl[1][1] if i > 0 and poscl[i - 1] > 0 else None

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
