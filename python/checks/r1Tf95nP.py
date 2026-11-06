"""Independent check — WJ BUY Strategy B (r1Tf95nP): daily bars, process_orders_on_close, pyramiding 50, one unit per lot (indep.simulate_pyr; the cash lot size does not change entries / exits). Score = [close < BB(40, 2) lower: 1.0]
+ [close < SMA400: 1.5, else < SMA240: 1.0, else < SMA120: 0.5] + [RSI14 <= 25: 2.0, <= 30: 1.5, <= 35: 1.0, <= 40: 0.5]. From 2021-01-01 (New York): score >= 3 arms mode 2; the score crossing up through 2 (previous < 2, now >= 2, mode != 2)
arms mode 1. While armed and the score is below its level the script counts days the score has not risen (reset to 0 on a rise); with days >= 2 and close >= SMA10 (two bars in a row when the close is below the last buy price) mode 1 buys "A"
(only if no earlier B price or close above it and the last B was >= 14 days ago) and mode 2 buys "B"; the mode then returns to 0. Flat resets the last-buy memory. close_all on the last bar. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_rsi, np_sma, run_conversion, simulate_pyr
from pinelib import SymbolInfo

TV_ID = "r1Tf95nP"


def check():
    df = bars(9000, seed=148)
    t = df["time"].to_numpy()
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    basis = np_sma(c, 40)
    lower = basis - 2.0 * pd.Series(c).rolling(40).std(ddof=0).to_numpy()
    m1, m2, m3 = np_sma(c, 120), np_sma(c, 240), np_sma(c, 400)
    rsi = np_rsi(c, 14)
    ema = np_sma(c, 10)
    start = int(pd.Timestamp("2021-01-01", tz="America/New_York").value // 1_000_000)
    fs = np.zeros(n)
    for i in range(n):
        s = 0.0
        with np.errstate(invalid="ignore"):
            if c[i] < lower[i]:
                s += 1.0
            if c[i] < m3[i]:
                s += 1.5
            elif c[i] < m2[i]:
                s += 1.0
            elif c[i] < m1[i]:
                s += 0.5
            r = rsi[i]
            if r <= 25:
                s += 2.0
            elif r <= 30:
                s += 1.5
            elif r <= 35:
                s += 1.0
            elif r <= 40:
                s += 0.5
        fs[i] = s
    S = dict(mode=0, days=0, bp=np.nan, bt=np.nan, lp=np.nan)

    def orders(i, pos):
        out = []
        if pos == 0:
            S.update(bp=np.nan, bt=np.nan, lp=np.nan)
        if t[i] >= start:
            prev = fs[i - 1] if i > 0 else np.nan
            if fs[i] >= 3.0:
                S.update(mode=2, days=0)
            elif prev < 2.0 and fs[i] >= 2.0 and S["mode"] != 2:
                S.update(mode=1, days=0)
            a_act = S["mode"] == 1 and fs[i] < 2.0
            b_act = S["mode"] == 2 and fs[i] < 3.0
            if a_act or b_act:
                if fs[i] > prev:
                    S["days"] = 0
                else:
                    S["days"] += 1
                cond_days = S["days"] >= 2
                lower_px = (not np.isnan(S["lp"])) and c[i] < S["lp"]
                with np.errstate(invalid="ignore"):
                    cond_ma = (c[i] >= ema[i] and c[i - 1] >= ema[i - 1]) if lower_px else (c[i] >= ema[i])
                if cond_days and cond_ma:
                    if S["mode"] == 1:
                        two_w = np.isnan(S["bt"]) or (t[i] - S["bt"] >= 14 * 86400000)
                        if (np.isnan(S["bp"]) or c[i] > S["bp"]) and two_w:
                            out.append(("entry", 1))
                            S["lp"] = c[i]
                        S["mode"] = 0
                    elif S["mode"] == 2:
                        out.append(("entry", 1))
                        S.update(bp=c[i], bt=t[i], lp=c[i], mode=0)
        if i == n - 1 and pos != 0 or (i == n - 1 and out):
            out.append(("close_all",))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate_pyr(o, h, l, c, orders, pyramiding=50, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
