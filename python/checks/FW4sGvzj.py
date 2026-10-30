"""Independent check — BTC Sell Strategy v2 (FW4sGvzj): hourly bars, short only. K = SMA3(stoch14(RSI14)), D = SMA3(K) (stoch of a flat series: ta.stoch(rsi, rsi, rsi) with ta.highest / lowest skipping the na RSI warm-up but needing 14 bars);
double top = K crossed over 80 within the last 10 bars (barssince(K[1] >= 80 and K[2] < 80) <= 10), K crosses under 80, K < D; VIX-Fix (highest close of 22 - low) / highest close * 100 < 2; close < 240-minute EMA200
(plain-pandas blocks from 09:30, lookahead off); 08:00-22:00 NY; cooldown > 10 bars since the last entry. The exit is re-issued every bar (stop = max(5-bar highest high, close + 2 ATR14), limit = close - 1.5 * (stop - close)); on a
bar where the open short is >= 0.8 R in profit (R = stop - avg) and the break-even move has not been done, it is re-issued with stop = min(avg, close + 1.5 ATR14) instead. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_cross_under, np_ema, np_periods, np_rsi, np_security_lookahead_off, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "FW4sGvzj"


def check():
    df = bars(50000, seed=299, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    rsi, atr = np_rsi(c, 14), np_atr(h, l, c, 14)
    hh = pd.Series(rsi).rolling(14, min_periods=1).max().to_numpy().copy()
    ll = pd.Series(rsi).rolling(14, min_periods=1).min().to_numpy().copy()
    hh[:13] = np.nan
    ll[:13] = np.nan
    with np.errstate(invalid="ignore", divide="ignore"):
        st_raw = 100 * (rsi - ll) / (hh - ll)
    st_raw[~np.isfinite(st_raw)] = np.nan
    k = np_sma(st_raw, 3)
    d = np_sma(k, 3)
    k1, k2 = np.r_[np.nan, k[:-1]], np.r_[np.nan, np.nan, k[:-2]]
    with np.errstate(invalid="ignore"):
        cond = (k1 >= 80) & (k2 < 80)
    since = np.full(n, np.nan)
    cnt = np.nan
    for i in range(n):
        cnt = 0 if cond[i] else (np.nan if np.isnan(cnt) else cnt + 1)
        since[i] = cnt
    pid, last_of = np_periods(df, 240)
    hc = pd.Series(c).groupby(pid).last().to_numpy()
    htf = np_security_lookahead_off(np_ema(hc, 200), pid, last_of)
    hc22 = pd.Series(c).rolling(22).max().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        vix = (hc22 - l) / hc22 * 100
        dtop = (since <= 10) & np_cross_under(k, 80.0) & (k < d)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    sess = (m >= 480) & (m < 1320)
    sw5 = pd.Series(h).rolling(5).max().to_numpy()
    st = dict(last=None, be=False)
    ep_now = {}
    lvl = np.full((n, 2), np.nan)

    def orders(i, pos):
        out = []
        ok = st["last"] is None or i - st["last"] > 10
        with np.errstate(invalid="ignore"):
            sig = bool(dtop[i] and vix[i] < 2.0 and c[i] < htf[i] and sess[i] and ok)
        if sig:
            out.append(("entry", -1)); st["last"] = i
        sl = max(sw5[i], c[i] + 2.0 * atr[i])
        tp = c[i] - 1.5 * (sl - c[i])
        lvl[i] = (sl, tp)
        if pos < 0:
            avg = ep_now.get(i, np.nan)
            with np.errstate(invalid="ignore", divide="ignore"):
                r = (avg - c[i]) / (sl - avg) if (sl - avg) != 0 else np.nan
                if not st["be"] and r >= 0.8:
                    lvl[i] = (min(avg, c[i] + 1.5 * atr[i]), tp)
                    st["be"] = True
        else:
            st["be"] = False
        return out

    def level(k_):
        def fn(i, pos, ep, eb):
            ep_now[i] = ep
            if i == 0 or np.isnan(lvl[i - 1][k_]):
                return None
            return lvl[i - 1][k_]
        return fn

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
