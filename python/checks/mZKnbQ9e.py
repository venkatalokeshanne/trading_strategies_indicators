"""Independent check — EQL/EQH Reversal (mZKnbQ9e): 5-min New York bars. Equal highs/lows: count of the 30 prior bars whose high is within 5 points of
the 30-bar high (or low of the 30-bar low); >= 2 plus the current bar touching it, inside 09:45-14:00 NY and only when flat, fades the extreme
(shorts take priority). Bracket 1.5 ATR stop / 2.5 ATR target from the signal close, working from the fill bar."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "mZKnbQ9e"


def check():
    df = bars(20000, seed=115, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    sess = (m >= 585) & (m < 840)
    atr = np_atr(h, l, c, 14)
    sc, lc = np.zeros(n, bool), np.zeros(n, bool)
    for i in range(30, n):
        hh, ll = h[i - 29:i + 1].max(), l[i - 29:i + 1].min()
        eqh = int((h[i - 30:i][::-1] >= hh - 5.0).sum())       # bars 1..30 back (the window is i-30 .. i-1)
        eql = int((l[i - 30:i][::-1] <= ll + 5.0).sum())
        sc[i] = eqh >= 2 and h[i] >= hh - 5.0
        lc[i] = eql >= 2 and l[i] <= ll + 5.0
    cur = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}
    hist = []

    def orders(i, pos):
        out = []
        short_sig = sess[i] and pos == 0 and sc[i]
        long_sig = sess[i] and pos == 0 and lc[i] and not short_sig
        if short_sig and not np.isnan(atr[i]):
            out.append(("entry", -1)); cur[-1] = (c[i] + atr[i] * 1.5, c[i] - atr[i] * 2.5)
        if long_sig and not np.isnan(atr[i]):
            out.append(("entry", 1)); cur[1] = (c[i] - atr[i] * 1.5, c[i] + atr[i] * 2.5)
        hist.append(dict(cur))
        return out

    ref = simulate(o, h, l, c, orders,
                   stop=lambda i, pos, ep, eb: hist[i - 1][pos][0] if i > 0 else None,
                   target=lambda i, pos, ep, eb: hist[i - 1][pos][1] if i > 0 else None)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
