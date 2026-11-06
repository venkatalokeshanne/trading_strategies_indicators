"""Independent check — Ichimoku TK-Cross + MFI (71yKm18B): 4-hour bars on a stock chart (New York clock), long only, market orders at the next open. Tenkan = mid of the 20-bar high / low, Kijun = mid of the 60-bar range, Senkou A = (Tenkan + Kijun) / 2, Senkou B = mid of the 120-bar range; the cloud 'now' is Senkou A / B 60 bars ago.
Entry (flat): Tenkan crosses over Kijun, close above the cloud top, MFI(hlc3, 14) > 50 (MFI = 100 - 100 / (1 + up / down) with money flow summed over 14 bars; the first bar's change is na, which counts as 'not <= 0', i.e. it enters both sums), and time >= the start date. Exit: close < Kijun (next open). The stop = cloud bottom is re-issued at every script run that
sees the position, so it works from the bar after the fill (a bar whose cloud value is na has no stop order). Variants: default start 2022 and start 2018. Slippage / margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "71yKm18B"


def mid(h, l, n):
    return (pd.Series(h).rolling(n, min_periods=n).max().to_numpy() + pd.Series(l).rolling(n, min_periods=n).min().to_numpy()) / 2.0


def np_mfi(src, vol, n):
    ch = np.r_[np.nan, np.diff(src)]
    up = vol * np.where(np.isnan(ch) | (ch > 0), src, 0.0)
    dn = vol * np.where(np.isnan(ch) | (ch < 0), src, 0.0)
    u = pd.Series(up).rolling(n, min_periods=n).sum().to_numpy()
    d = pd.Series(dn).rolling(n, min_periods=n).sum().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        out = 100.0 - 100.0 / (1.0 + u / d)
    return out


def one(df, params, year):
    o, h, l, c, v, t = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume", "time"))
    n = len(c)
    ten, kij = mid(h, l, 20), mid(h, l, 60)
    la, lb = (ten + kij) / 2.0, mid(h, l, 120)
    sh = lambda x, k: np.r_[np.full(k, np.nan), x[:-k]]
    la60, lb60 = sh(la, 60), sh(lb, 60)
    top, bot = np.fmax(la60, lb60), np.fmin(la60, lb60)
    mfi = np_mfi((h + l + c) / 3.0, v, 14)
    t0 = pd.Timestamp(year=year, month=1, day=1, tz="America/New_York").value // 10**6
    t1 = pd.Timestamp(year=2099, month=12, day=31, hour=23, minute=59, tz="America/New_York").value // 10**6
    tc = (t >= t0) & (t <= t1)
    with np.errstate(invalid="ignore"):
        lc = np_cross_over(ten, kij) & (c > top) & (mfi > 50.0) & tc
        xc = (c < kij) & tc
    poscl = np.zeros(n)
    stop_arr = np.full(n, np.nan)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if lc[i] and pos == 0:
            out.append(("entry", 1))
        if xc[i] and pos > 0:
            out.append(("close", 1))
        if pos > 0:
            stop_arr[i] = bot[i]
        return out

    stop = lambda i, pos, ep, eb: None if (i == 0 or eb >= i or poscl[i - 1] <= 0 or np.isnan(stop_arr[i - 1])) else stop_arr[i - 1]
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="240", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(60000, seed=721, freq="4h")
    msgs, allok = [], True
    for params, y in (({}, 2022), ({"Start year": 2018}, 2018)):
        ok, m = one(df, params, y)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
