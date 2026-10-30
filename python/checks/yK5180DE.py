"""Independent check — Scalping London New York (yK5180DE): 5-min bars (SMA 12/56), pyramiding 10 (indep.simulate_pyr), 1 unit per lot. Signal on bar i (hour filter on the bar's New York hour): the previous bar was up and fast SMA[1] > slow SMA[1]
(long) or down and fast[1] < slow[1] (short). Flat -> open one lot; opposite signal -> close; in position -> add a lot each time the close is a step beyond the last entry (max 10 lots; a close signal resets the last-entry price, so no add on that bar).
Stop / limit around the average price of the lots filled by the signal bar's close are issued from that close, so they work from the next bar on the whole stack (lots filled at that next open included).
The synthetic price is ~100, so the stop / take-profit / step inputs are scaled up (pips = 0.01) to 3.0 / 4.0 / 1.0 dollars; both sides get the same inputs."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_sma, run_conversion, simulate_pyr
from pinelib import SymbolInfo

TV_ID = "yK5180DE"
SL, TP, STEP = 300.0, 400.0, 100.0


def check():
    df = bars(9000, seed=611, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    hour = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York").dt.hour.to_numpy()
    fast, slow = np_sma(c, 12), np_sma(c, 56)
    allowed = (hour >= 7) & (hour <= 17)
    f1, s1 = np.r_[np.nan, fast[:-1]], np.r_[np.nan, slow[:-1]]
    o1, c1 = np.r_[np.nan, o[:-1]], np.r_[np.nan, c[:-1]]
    with np.errstate(invalid="ignore"):
        ls = allowed & (o1 < c1) & (f1 > s1)
        ss = allowed & (o1 > c1) & (f1 < s1)
    last = [np.nan]
    cnt = [0]
    avgs = np.full(n, np.nan)

    def orders(i, pos):
        out = []
        if pos == 0:
            cnt[0] = 0
            last[0] = np.nan
        if ls[i] and pos < 0:
            out.append(("close", -1))
            last[0], cnt[0] = np.nan, 0
        if ss[i] and pos > 0:
            out.append(("close", 1))
            last[0], cnt[0] = np.nan, 0
        if ls[i] and pos == 0:
            out.append(("entry", 1))
            last[0], cnt[0] = c[i], 1
        if ss[i] and pos == 0:
            out.append(("entry", -1))
            last[0], cnt[0] = c[i], 1
        if pos > 0 and cnt[0] < 10 and not np.isnan(last[0]) and c[i] <= last[0] - 0.01 * STEP:
            out.append(("entry", 1))
            last[0], cnt[0] = c[i], cnt[0] + 1
        if pos < 0 and cnt[0] < 10 and not np.isnan(last[0]) and c[i] >= last[0] + 0.01 * STEP:
            out.append(("entry", -1))
            last[0], cnt[0] = c[i], cnt[0] + 1
        return out

    def avg_prev(i, trades):
        old = [t[2] for t in trades if t[1] < i]
        return np.mean(old) if old else None

    def stop(i, d, trades):
        a = avg_prev(i, trades)
        return None if a is None else (a - 0.01 * SL if d > 0 else a + 0.01 * SL)

    def target(i, d, trades):
        a = avg_prev(i, trades)
        return None if a is None else (a + 0.01 * TP if d > 0 else a - 0.01 * TP)

    with np.errstate(invalid="ignore"):
        ref = simulate_pyr(o, h, l, c, orders, pyramiding=10, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    params = {"Stop Loss Request": SL, "Take Profit Request": TP, "Nanpin Step Request": STEP}
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
