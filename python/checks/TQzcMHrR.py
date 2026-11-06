"""Independent check — Booming Bull (TQzcMHrR): 15-min continuous bars. Pivots from the previous trading day (09:30-NY blocks; the daily security with lookahead on shows yesterday's H/L/C on every bar of the day): P = (H+L+C)/3, R1 = 2P-L, S1 = 2P-H, R2 = P+(H-L), S2 = P-(H-L), R3 = H+2(P-L), S3 = L-2(H-P).
The seven crossover / crossunder calls in the `or` chain only run (and only advance their own previous-value history) on bars where every earlier one was false. Entry (efficiency filter on): IST 09:15-15:00 session, close vs VWAP(hlc3, 09:30-NY reset), Stoch RSI K vs D (K = SMA3 of the raw stoch of RSI14, D = SMA3 of K, prefix-sum
SMAs so exact K == D plateaus tie as in pinelib) and a pivot cross; flat -> short with stop = high, target = close - 1.5 risk (long mirrored with the low); IST minutes >= 900 closes any position (at the next open)."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_periods, np_rsi, np_vwap, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "TQzcMHrR"


def psma(x, n):
    x = np.asarray(x, float)
    nanc = np.r_[0, np.cumsum(np.isnan(x))]
    P = np.r_[0.0, np.cumsum(np.where(np.isnan(x), 0.0, x))]
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        if nanc[i + 1] - nanc[i - n + 1] == 0:
            out[i] = (P[i] - P[i - (n - 1)] + x[i]) / n
    return out


def check():
    df = bars(14000, seed=200, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    pid, _ = np_periods(df, 1440)
    k_ = pid.max() + 1
    dh = pd.Series(h).groupby(pid).max().to_numpy()
    dl = pd.Series(l).groupby(pid).min().to_numpy()
    dc = np.array([c[pid == p][-1] for p in range(k_)])
    ph = np.where(pid > 0, dh[np.maximum(pid - 1, 0)], np.nan)
    pl = np.where(pid > 0, dl[np.maximum(pid - 1, 0)], np.nan)
    pc = np.where(pid > 0, dc[np.maximum(pid - 1, 0)], np.nan)
    p = (ph + pl + pc) / 3
    lv = [p, 2 * p - pl, p + (ph - pl), ph + 2 * (p - pl), 2 * p - ph, p - (ph - pl), pl - 2 * (ph - p)]
    vw = np_vwap(df, (h + l + c) / 3)
    rsi = np_rsi(c, 14)
    hh = pd.Series(rsi).rolling(14, min_periods=1).max().to_numpy().copy()
    ll = pd.Series(rsi).rolling(14, min_periods=1).min().to_numpy().copy()
    hh[:13] = ll[:13] = np.nan
    with np.errstate(invalid="ignore", divide="ignore"):
        raw = 100 * (rsi - ll) / (hh - ll)
    raw[~np.isfinite(raw)] = np.nan
    K = psma(raw, 3)
    D = psma(K, 3)
    ist = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Asia/Kolkata")
    mins = (ist.dt.hour * 60 + ist.dt.minute).to_numpy()
    insess = (mins >= 555) & (mins < 900)
    down_prev = [None] * 7
    up_prev = [None] * 7

    def chain(i, prev, under):
        res = False
        for j in range(7):
            lvl = lv[j][i]
            pv = prev[j]
            if pv is not None:
                with np.errstate(invalid="ignore"):
                    cond = (c[i] < lvl and pv[0] >= pv[1]) if under else (c[i] > lvl and pv[0] <= pv[1])
            else:
                cond = False
            prev[j] = (c[i], lvl)
            if cond:
                res = True
                break
        return res

    lvl_ = {}

    def orders(i, pos):
        out = []
        pcd = chain(i, down_prev, True)
        pcu = chain(i, up_prev, False)
        with np.errstate(invalid="ignore"):
            sell = insess[i] and c[i] < vw[i] and K[i] < D[i] and pcd
            buy = insess[i] and c[i] > vw[i] and K[i] > D[i] and pcu
        if sell and pos == 0:
            risk = h[i] - c[i]
            lvl_[-1] = (h[i], c[i] - risk * 1.5)
            out.append(("entry", -1))
        if buy and pos == 0:
            risk = c[i] - l[i]
            lvl_[1] = (l[i], c[i] + risk * 1.5)
            out.append(("entry", 1))
        if mins[i] >= 900 and pos != 0:
            out.append(("close", 1 if pos > 0 else -1))
        return out

    def stop(i, pos, ep, eb):
        return lvl_[1 if pos > 0 else -1][0]

    def target(i, pos, ep, eb):
        return lvl_[1 if pos > 0 else -1][1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
