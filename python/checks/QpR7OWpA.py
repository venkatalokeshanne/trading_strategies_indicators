"""Independent check — SMC ICT Backtest (QpR7OWpA): 5-min New York bars, process_orders_on_close. Confirmed pivots (5 left / 5 right,
reported on the bar the 5th right bar closes) feed lastHigh/lastLow; a sweep of the last pivot with a close back through it, a close
beyond the prior bar's extreme and a 3-bar gap, inside 07:00-10:00 or 12:30-16:00 NY, enters at the close with stop = signal bar low/high
and target 2R, working from the next bar (opposite entries reverse; same-direction ones are ignored)."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "QpR7OWpA"


def check():
    df = bars(40000, seed=113, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    sess = ((m >= 420) & (m < 600)) | ((m >= 750) & (m < 960))
    lastH, lastL = np.nan, np.nan
    buy, sell = np.zeros(n, bool), np.zeros(n, bool)
    h1, l1 = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    h2, l2 = np.r_[[np.nan] * 2, h[:-2]], np.r_[[np.nan] * 2, l[:-2]]
    for i in range(n):
        if i >= 10:
            ctr = i - 5
            if h[ctr] > h[i - 10:ctr].max() and h[ctr] > h[ctr + 1:i + 1].max():
                lastH = h[ctr]
            if l[ctr] < l[i - 10:ctr].min() and l[ctr] < l[ctr + 1:i + 1].min():
                lastL = l[ctr]
        bs = not np.isnan(lastL) and l[i] < lastL and c[i] > lastL
        ss = not np.isnan(lastH) and h[i] > lastH and c[i] < lastH
        bull = bs and c[i] > h1[i] and l[i] > h2[i]
        bear = ss and c[i] < l1[i] and h[i] < l2[i]
        buy[i], sell[i] = sess[i] and bull, sess[i] and bear
    lv = {1: [], -1: []}
    cur = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}
    for j in range(n):
        if buy[j]:
            cur[1] = (l[j], c[j] + (c[j] - l[j]) * 2.0)
        if sell[j]:
            cur[-1] = (h[j], c[j] - (h[j] - c[j]) * 2.0)
        lv[1].append(cur[1]); lv[-1].append(cur[-1])

    def level(k):
        return lambda i, pos, ep, eb: lv[pos][i - 1][k] if (i > 0 and i > eb) else None

    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if buy[i] else []) + ([("entry", -1)] if sell[i] else []),
                   stop=level(0), target=level(1), on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
