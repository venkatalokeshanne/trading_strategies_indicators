"""Independent check — ES ORB (RlBmis1p): 5-min New York bars on a mean-reverting synthetic index around 5000 (OU, so the 32 / 64 point bracket is meaningful). Opening range = high / low of the bars starting 09:30-09:45
(reset at the first bar of each trading day, days from 09:30). After 09:45, a close crossing over the range high above session VWAP and the 15-minute EMA20 (plain-pandas 15-minute blocks, lookahead off) goes long (mirror short),
while flat, at most 2 trades a day and one per side. While a position is open at a close, stop 32 / limit 64 points around the entry price, working from the next bar. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import compare, np_cross_over, np_cross_under, np_ema, np_periods, np_security_lookahead_off, np_vwap, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "RlBmis1p"


def ou_bars(n, seed, mu, theta, sigma, freq="5min"):
    rng = np.random.default_rng(seed)
    x = np.empty(n)
    x[0] = mu
    for i in range(1, n):
        x[i] = x[i - 1] + theta * (mu - x[i - 1]) + sigma * rng.normal()
    open_ = np.r_[x[0], x[:-1]] + rng.normal(0, sigma / 8, n)
    high = np.maximum(open_, x) + np.abs(rng.normal(0, sigma / 2, n))
    low = np.minimum(open_, x) - np.abs(rng.normal(0, sigma / 2, n))
    t = pd.date_range("2015-01-01", periods=n, freq=freq, tz="UTC").as_unit("ms").asi8
    return pd.DataFrame({"time": t, "open": open_, "high": high, "low": low, "close": x, "volume": rng.integers(1000, 100000, n).astype(float)})


def check():
    df = ou_bars(40000, 262, 5000.0, 0.002, 3.0)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    day, _ = np_periods(df, 1440)
    in_orb = (m >= 570) & (m <= 585)
    after = m > 585
    vw = np_vwap(df, c)
    pid, last_of = np_periods(df, 15)
    hc = pd.Series(c).groupby(pid).last().to_numpy()
    hclose = np_security_lookahead_off(hc, pid, last_of)
    hema = np_security_lookahead_off(np_ema(hc, 20), pid, last_of)
    orh = orl = np.nan
    ohs, ols = np.full(n, np.nan), np.full(n, np.nan)
    cnt, lt, st_ = 0, False, False
    for i in range(n):
        if i == 0 or day[i] != day[i - 1]:
            orh = orl = np.nan
        if in_orb[i]:
            orh = h[i] if np.isnan(orh) else max(orh, h[i])
            orl = l[i] if np.isnan(orl) else min(orl, l[i])
        ohs[i], ols[i] = orh, orl
    with np.errstate(invalid="ignore"):
        lb = after & ~np.isnan(ohs) & np_cross_over(c, ohs)
        sb = after & ~np.isnan(ols) & np_cross_under(c, ols)
        lc = lb & (c > vw) & (hclose > hema)
        sc = sb & (c < vw) & (hclose < hema)
    state = dict(cnt=0, lt=False, st=False)

    def orders(i, pos):
        if i == 0 or day[i] != day[i - 1]:
            state.update(cnt=0, lt=False, st=False)
        out = []
        if lc[i] and pos == 0 and state["cnt"] < 2 and not state["lt"]:
            out.append(("entry", 1)); state["cnt"] += 1; state["lt"] = True
        if sc[i] and pos == 0 and state["cnt"] < 2 and not state["st"]:
            out.append(("entry", -1)); state["cnt"] += 1; state["st"] = True
        return out

    ref = simulate(o, h, l, c, orders,
                   stop=lambda i, pos, ep, eb: None if eb >= i else ep - pos * 32.0,
                   target=lambda i, pos, ep, eb: None if eb >= i else ep + pos * 64.0)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
