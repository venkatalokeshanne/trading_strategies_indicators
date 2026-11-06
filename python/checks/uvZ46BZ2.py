"""Independent check — BB + RSI + Volume + EMA + ADX (uvZ46BZ2): 15-min continuous bars, next-open fills. Buy: close >= BB(20,2) upper (population stdev), previous close < the CURRENT upper band, RSI14 > 60, volume > SMA20, close > EMA200, ADX14 > 20 and rising, +DI > -DI; sell mirrors (RSI < 40, close < EMA200, -DI > +DI).
Entries ignore an already-open same-side trade; the stop variable is refreshed only on a signal while flat (low / high of the signal bar). Both exit orders are rebuilt every bar from the position average price at script time: risk = min(entry - SL, 1.5% of entry) (short: SL - entry), stop = entry -/+ risk, target = entry +/- 2 risk (na while
flat or SL na); they work from the next bar, each for its own direction even right after a reversal. 15:15-15:59 New York closes any open position."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_dmi, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "uvZ46BZ2"


def check():
    df = bars(16000, seed=170, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    ex_t = ((ny.dt.hour == 15) & (ny.dt.minute >= 15)).to_numpy()
    basis = np_sma(c, 20)
    dev = 2.0 * pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    up, lo = basis + dev, basis - dev
    c1 = np.r_[np.nan, c[:-1]]
    rsi, ema = np_rsi(c, 14), np_ema(c, 200)
    dp, dm, adx = np_dmi(h, l, c, 14)
    adx1 = np.r_[np.nan, adx[:-1]]
    with np.errstate(invalid="ignore"):
        vc = v > np_sma(v, 20)
        common = vc & (adx > 20) & (adx > adx1)
        buy = (c >= up) & (c1 < up) & (rsi > 60) & (c > ema) & (dp > dm) & common
        sell = (c <= lo) & (c1 > lo) & (rsi < 40) & (c < ema) & (dm > dp) & common
    S = dict(lsl=np.nan, ssl=np.nan)
    tmp, lv = {}, {}

    def levels(ep, d):
        if d > 0:
            risk = min(ep - S["lsl"], ep * 0.015)
            return ep - risk, ep + 2 * risk
        risk = min(S["ssl"] - ep, ep * 0.015)
        return ep + risk, ep - 2 * risk

    def orders(i, pos):
        out = []
        if buy[i]:
            out.append(("entry", 1))
        if sell[i]:
            out.append(("entry", -1))
        if buy[i] and pos == 0:
            S["lsl"] = l[i]
        if sell[i] and pos == 0:
            S["ssl"] = h[i]
        ep = tmp.get(i) if pos != 0 else None
        with np.errstate(invalid="ignore"):
            lv[i] = None if ep is None else (levels(ep, 1), levels(ep, -1))
        if ex_t[i] and pos != 0:
            out.append(("close", 1 if pos > 0 else -1))
        return out

    def stop(i, pos, ep, eb):
        tmp[i] = ep
        p = lv.get(i - 1) if i > 0 else None
        lev = None if p is None else p[0] if pos > 0 else p[1]
        return None if lev is None or np.isnan(lev[0]) else lev[0]

    def target(i, pos, ep, eb):
        p = lv.get(i - 1) if i > 0 else None
        lev = None if p is None else p[0] if pos > 0 else p[1]
        return None if lev is None or np.isnan(lev[1]) else lev[1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
