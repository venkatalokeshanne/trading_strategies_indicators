"""Independent check — NQ 21 EMA Root Pullback v4 (A8q809pu): 5-min New York bars shifted to start on 2026-04-01 (the script only trades 2026-04-01 .. 2026-05-01). 09:30-12:00 NY, SMA21 of
the EMA21 as "root"; long when root < EMA and the close is > 10 points over the EMA after the previous bar's low touched it, on a green candle breaking the previous high (shorts mirrored);
2 trades a day (counter reset on the first bar of each trading day), only when flat. Exits unconditional, pending before the fill: loss 20 ticks / profit 80 ticks (0.01)."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "A8q809pu"


def check():
    df = bars(9000, seed=183, freq="5min")
    ny0 = pd.Timestamp("2026-04-01 00:00", tz="America/New_York")
    df["time"] = df["time"] - df["time"].iloc[0] + int(ny0.tz_convert("UTC").value // 1_000_000)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    sess = (m >= 570) & (m < 720)
    in_range = (ny >= ny0).to_numpy() & (ny <= pd.Timestamp("2026-05-01 23:59", tz="America/New_York")).to_numpy()
    key = (ny - pd.Timedelta(minutes=570)).dt.date.to_numpy()
    e = np_ema(c, 21)
    root = np_sma(e, 21)
    pe, pl, ph = np.r_[np.nan, e[:-1]], np.r_[np.nan, l[:-1]], np.r_[np.nan, h[:-1]]
    with np.errstate(invalid="ignore"):
        lg = in_range & sess & (root < e) & (c > e + 10) & (pl <= pe) & (c > o) & (c > ph) & (c > e)
        sg = in_range & sess & (root > e) & (c < e - 10) & (ph >= pe) & (c < o) & (c < np.r_[np.nan, l[:-1]]) & (c < e)
    cnt = [0]

    def orders(i, pos):
        out = []
        if i > 0 and key[i] != key[i - 1]:
            cnt[0] = 0
        if lg[i] and pos == 0 and cnt[0] < 2:
            out.append(("entry", 1)); cnt[0] += 1
        if sg[i] and pos == 0 and cnt[0] < 2:
            out.append(("entry", -1)); cnt[0] += 1
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: ep - pos * 20 * 0.01, target=lambda i, pos, ep, eb: ep + pos * 80 * 0.01)
    sym = SymbolInfo.make("NASDAQ:NQ", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
