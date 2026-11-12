"""Independent check — Universal Backtest Pro (PyL6RfBr; PyL6RfBr is the same script): daily bars, analysis timeframe D (= the chart), slippage 0, all five selectable signal sets are run in turn (EMA crossover with EMA200 regime, RSI [long on a cross DOWN through 30, short on a cross UP through 70 - as written], MACD cross, Bollinger re-entry [close crossing over the
lower / under the upper band], SuperTrend flip). Window 2020-01-01 to 2030-12-31 UTC. Signals flip the position at the next open. While a position exists (as of a bar's close) its own-direction stop (2%), target (4%) and trailing stop (arm 2% of the average price, offset 1%, in ticks of 0.01) around the position average price are issued and work from the next bar."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, np_rsi, np_sma, np_supertrend, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "PyL6RfBr"


def one(df, name, long_sig, short_sig, inr):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    poscl = np.zeros(n)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if inr[i] and long_sig[i]:
            out.append(("entry", 1))
        if inr[i] and short_sig[i]:
            out.append(("entry", -1))
        return out

    def stop(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0:
            return None
        return ep * 0.98 if pos > 0 else ep * 1.02

    def target(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0:
            return None
        return ep * 1.04 if pos > 0 else ep * 0.96

    def trail(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0:
            return None
        return (ep * 0.04 / 2 / 0.01, ep * 0.02 / 2 / 0.01)

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target, trail=trail, tick=0.01)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Select Strategy": name}, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 5, f"{name}: {detail} (got {len(ref)})"


def check():
    df = bars(9000, seed=490)
    h, l, c = (df[k].to_numpy() for k in ("high", "low", "close"))
    t0 = int(pd.Timestamp("2020-01-01", tz="UTC").value // 1_000_000)
    t1 = 1924991999000
    inr = (df["time"].to_numpy() >= t0) & (df["time"].to_numpy() <= t1)
    msgs, allok = [], True
    f, s, rg = np_ema(c, 9), np_ema(c, 21), np_ema(c, 200)
    rsi = np_rsi(c, 14)
    macd = np_ema(c, 12) - np_ema(c, 26)
    sig = np_ema(macd, 9)
    basis = np_sma(c, 20)
    dev = 2.0 * pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    _, d = np_supertrend(h, l, c, 3.0, 10)
    dd = d - np.r_[np.nan, d[:-1]]
    with np.errstate(invalid="ignore"):
        sets = {
            "EMA Crossover": (np_cross_over(f, s) & (c > rg), np_cross_under(f, s) & (c < rg)),
            "RSI Strategy": (np_cross_under(rsi, 30.0), np_cross_over(rsi, 70.0)),
            "MACD Strategy": (np_cross_over(macd, sig), np_cross_under(macd, sig)),
            "Bollinger Bands Breakout": (np_cross_over(c, basis - dev), np_cross_under(c, basis + dev)),
            "SuperTrend": (dd < 0, dd > 0),
        }
    for name, (ls, ss) in sets.items():
        ok, m = one(df, name, ls, ss, inr)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
