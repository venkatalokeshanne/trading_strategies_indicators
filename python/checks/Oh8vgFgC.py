"""Independent check — WJ Strategy A (Oh8vgFgC): daily bars, cash-sized pyramiding (20) entries filled at the signal close (process_orders_on_close). Score = BB(40,2) lower break 1 + SMA120/240/400 break 0.5/1/1.5 +
RSI<=40/35/30/25 0.5/1/1.5/2; reaching 2.0 arms a monitor; below it, a non-rising score for 2 days with close >= SMA10 enters and disarms; the last bar closes everything. Start date 2015 (whole sample)."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_rsi, np_sma, run_conversion, simulate_pyr
from pinelib import SymbolInfo

TV_ID = "Oh8vgFgC"
TH = 2.0


def check():
    df = bars(5000, seed=31)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sd = pd.Series(c).rolling(40).std(ddof=0).to_numpy()
    lower = np_sma(c, 40) - 2.0 * sd
    m1, m2, m3 = np_sma(c, 120), np_sma(c, 240), np_sma(c, 400)
    rsi = np_rsi(c, 14)
    ema10 = np_sma(c, 10)
    score = np.zeros(n)
    with np.errstate(invalid="ignore"):
        for i in range(n):
            s = 1.0 if c[i] < lower[i] else 0.0
            s += 1.5 if c[i] < m3[i] else 1.0 if c[i] < m2[i] else 0.5 if c[i] < m1[i] else 0.0
            s += 2.0 if rsi[i] <= 25 else 1.5 if rsi[i] <= 30 else 1.0 if rsi[i] <= 35 else 0.5 if rsi[i] <= 40 else 0.0
            score[i] = s
    st = {"mon": False, "days": 0}

    def orders(i, pos):
        out = []
        if score[i] >= TH:
            st["mon"], st["days"] = True, 0
        if st["mon"] and score[i] < TH:
            if i > 0 and score[i] > score[i - 1]:
                st["days"] = 0
            else:
                st["days"] += 1
                if st["days"] >= 2 and c[i] >= ema10[i]:
                    out.append(("entry", 1))
                    st["mon"] = False
        if i == n - 1:
            out.append(("close_all",))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate_pyr(o, h, l, c, orders, pyramiding=20, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"시작 연도": 2015},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
