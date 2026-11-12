"""Independent check — EMA Ride V2 (GDcSJIo9): daily bars, slippage 0, thresholds loosened and passed to both sides (min weeks 2, dip zone 8%, min bounces 1, min % above EMA9 50, min ATR 1.0%, min above 52W low 10%). Stack = EMA9 > EMA21 > EMA50; barsAbove = consecutive closes above EMA21; 60-bar share of closes above EMA9; 90-bar count of bars with low <= 1.02 EMA21 and close > EMA9;
dist = (close - EMA9)/EMA9*100 in [0, 8]; EMA9 > EMA9[3]; ATR14/close*100 >= 1; 100*(close - lowest low 252)/lowest >= 10. Entry at the next open when flat; exit (EMA21 Close mode) when close < EMA21, at the next open."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "GDcSJIo9"
P = {"Min Weeks Riding EMA21": 2, "Entry Dip Zone % above EMA9": 8.0, "Min Cloud Bounces (90 bars)": 1, "Min % bars above EMA9 (60 bars)": 50.0,
     "Min ATR %": 1.0, "Min % above 52W Low": 10.0}


def check():
    df = bars(9000, seed=135)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    e9, e21, e50 = np_ema(c, 9), np_ema(c, 21), np_ema(c, 50)
    with np.errstate(invalid="ignore"):
        stack = (e9 > e21) & (e21 > e50)
        above21 = (c > e21).astype(int)
        gb = ((l <= e21 * 1.02) & (c > e9)).astype(int)
        ab9 = (c > e9).astype(int)
    run = np.zeros(n, int)
    for i in range(n):
        run[i] = run[i - 1] + 1 if (i and above21[i]) else (1 if above21[i] else 0)
    s60 = pd.Series(ab9).rolling(60).sum().to_numpy()
    s90 = pd.Series(gb).rolling(90).sum().to_numpy()
    pct9 = s60 / 60.0 * 100
    dist = (c - e9) / e9 * 100
    e93 = np.r_[[np.nan] * 3, e9[:-3]]
    atrp = np_atr(h, l, c, 14) / c * 100
    low52 = pd.Series(l).rolling(252).min().to_numpy()
    p52 = (c - low52) / low52 * 100
    mb = P["Min Weeks Riding EMA21"] * 5
    with np.errstate(invalid="ignore"):
        at_dip = (dist >= 0) & (dist <= 8.0) & (run >= mb) & (s90 >= 1) & stack & (e9 > e93)
        vcps = (atrp >= 1.0) & (p52 >= 10.0) & stack
        entry = at_dip & vcps
        ex = c < e21

    def orders(i, pos):
        out = []
        if entry[i] and pos == 0:
            out.append(("entry", 1))
        if pos > 0 and ex[i]:
            out.append(("close", 1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params=P, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
