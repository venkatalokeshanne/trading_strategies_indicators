"""Independent check — HTF EMA Pullback (LZ90uP19): 1h continuous bars, daily (09:30-NY) EMA9/EMA21 of the period closes with lookahead off as the direction filter, orders at the signal close (process_orders_on_close), qty irrelevant. touched = min over the last 6 bars of |low - EMA9|/EMA9 <= 0.2%; candle: bull/bear engulfing or a
wick > 40% of the range; MACD(12,26,9) histogram improving (> / < previous); close beyond EMA9. Stop = latest confirmed pivot low (long) / high (short) (2 bars each side, strict), target = close +/- 1.5 x distance to it; an entry needs the stop on the right side of the close. Entries reverse an open opposite trade and replace the bracket."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, np_periods, np_security_lookahead_off, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "LZ90uP19"


def check():
    df = bars(12000, seed=350, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    pid, last_of = np_periods(df, 1440)
    pc = np.array([c[last_of & (pid == k)][0] for k in range(pid[-1] + 1)])
    he9 = np_security_lookahead_off(np_ema(pc, 9), pid, last_of)
    he21 = np_security_lookahead_off(np_ema(pc, 21), pid, last_of)
    e9 = np_ema(c, 9)
    macd = np_ema(c, 12) - np_ema(c, 26)
    hist = macd - np_ema(macd, 9)
    hist1 = np.r_[np.nan, hist[:-1]]
    dist = np.abs(l - e9) / e9
    touched = pd.Series(dist).rolling(6).min().to_numpy() <= 0.002
    c1, o1 = np.r_[np.nan, c[:-1]], np.r_[np.nan, o[:-1]]
    rng = h - l + 1e-10
    lw = np.where(l < o, o - l, c - l) / rng
    uw = np.where(h > o, h - o, h - c) / rng
    with np.errstate(invalid="ignore"):
        be = (c > o) & (o <= c1) & (o1 > c1) & (c >= o1)
        se = (c < o) & (o >= c1) & (o1 < c1) & (c <= o1)
        lset = (he9 > he21) & touched & (be | (lw > 0.4)) & (hist > hist1) & (c > e9)
        sset = (he9 < he21) & touched & (se | (uw > 0.4)) & (hist < hist1) & (c < e9)
    s = dict(ls=np.nan, ss=np.nan)
    lvl = {}

    def orders(i, pos):
        out = []
        if i >= 4:
            m = i - 2
            w = l[m - 2:m + 3]
            if l[m] == w.min() and (w == l[m]).sum() == 1:
                s["ls"] = l[m]
            w = h[m - 2:m + 3]
            if h[m] == w.max() and (w == h[m]).sum() == 1:
                s["ss"] = h[m]
        with np.errstate(invalid="ignore"):
            if lset[i] and not np.isnan(s["ls"]) and c[i] > s["ls"]:
                out.append(("entry", 1))
                lvl[1] = (s["ls"], c[i] + (c[i] - s["ls"]) * 1.5)
            if sset[i] and not np.isnan(s["ss"]) and c[i] < s["ss"]:
                out.append(("entry", -1))
                lvl[-1] = (s["ss"], c[i] - (s["ss"] - c[i]) * 1.5)
        return out

    def stop(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][0]

    def target(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
