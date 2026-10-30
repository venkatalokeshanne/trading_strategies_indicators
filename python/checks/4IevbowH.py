"""Independent check — Asia Liquidity Sweep Scalper (4IevbowH): 5-min New York bars. Pivots (3 each side, strict) give lastPH / lastPL (updated on the confirmation bar). In the 19:00-00:00 New York session: low < lastPL and close >
lastPL with RSI14 <= 45, flat, goes long (mirrored: short with RSI >= 55). Unconditional exits at the position's average price as of the previous close, stop 1.2 ATR / limit 1.4 ATR of that bar (none on a fill bar).
The first bar a position is open at the close sets entryBarIndex; held = bar - entry bar >= 25 closes everything at the next open. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "4IevbowH"
K = 3


def conf(x, high):
    n = len(x)
    out = np.full(n, np.nan)
    for i in range(2 * K, n):
        j = i - K
        if high and x[j] > x[j - K:j].max() and x[j] > x[j + 1:i + 1].max():
            out[i] = x[j]
        if (not high) and x[j] < x[j - K:j].min() and x[j] < x[j + 1:i + 1].min():
            out[i] = x[j]
    return out


def check():
    df = bars(40000, seed=290, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    sess = ((ny.dt.hour * 60 + ny.dt.minute) >= 1140).to_numpy()
    cph, cpl = conf(h, True), conf(l, False)
    rsi, atr = np_rsi(c, 14), np_atr(h, l, c, 14)
    lph = lpl = np.nan
    ep_now, avg_close, poscl = {}, np.full(n, np.nan), np.zeros(n)
    eb = [None]

    def orders(i, pos):
        nonlocal lph, lpl
        poscl[i] = pos
        avg_close[i] = ep_now.get(i, np.nan) if pos != 0 else np.nan
        if not np.isnan(cph[i]):
            lph = cph[i]
        if not np.isnan(cpl[i]):
            lpl = cpl[i]
        out = []
        with np.errstate(invalid="ignore"):
            if sess[i] and not np.isnan(lpl) and l[i] < lpl and c[i] > lpl and rsi[i] <= 45 and pos == 0:
                out.append(("entry", 1))
            if sess[i] and not np.isnan(lph) and h[i] > lph and c[i] < lph and rsi[i] >= 55 and pos == 0:
                out.append(("entry", -1))
        if pos != 0 and eb[0] is None:
            eb[0] = i
        if pos == 0:
            eb[0] = None
        if pos != 0 and i - eb[0] >= 25:
            out.append(("close", pos))
        return out

    def level(k):
        def fn(i, pos, ep, eb_):
            ep_now[i] = ep
            if i == 0 or np.isnan(avg_close[i - 1]) or np.isnan(atr[i - 1]):
                return None
            a = avg_close[i - 1]
            if k == 0:
                return a - pos * 1.2 * atr[i - 1]
            return a + pos * 1.4 * atr[i - 1]
        return fn

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
