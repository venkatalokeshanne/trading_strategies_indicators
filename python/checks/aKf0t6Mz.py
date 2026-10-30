"""Independent check — EMA 5/13/26 cross (aKf0t6Mz): 15-min bars, orders at the signal close (process_orders_on_close). EMA5 crossing above both EMA13 and EMA26 (previous bar below both) with volume > SMA20 buys, mirror sells, closing the opposite side first.
Signal-candle variables (SL = low/high, candle high / low) are refreshed only on a signal while flat. Both exits are rebuilt every bar from the position average price (na while flat): risk = min(entry - SL, 1% of entry) (short: SL - entry), RR = 1 if
(signal high - signal low)/signal low*100 > 1 else 2, stop = entry -/+ risk, target = entry +/- RR*risk; they apply from the bar after the one that computed them, and each order (long / short) applies to the trade of its own direction even when the average price came from the opposite trade (a reversal bar). 23:10-23:59 New York closes any open position."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "aKf0t6Mz"


def check():
    df = bars(14000, seed=59, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    ex_t = ((ny.dt.hour == 23) & (ny.dt.minute >= 10)).to_numpy()
    e5, e13, e26 = np_ema(c, 5), np_ema(c, 13), np_ema(c, 26)
    p5, p13, p26 = (np.r_[np.nan, x[:-1]] for x in (e5, e13, e26))
    with np.errstate(invalid="ignore"):
        vc = v > np_sma(v, 20)
        buy = (p5 < p13) & (p5 < p26) & (e5 > e13) & (e5 > e26) & vc
        sell = (p5 > p13) & (p5 > p26) & (e5 < e13) & (e5 < e26) & vc
    S = dict(lsl=np.nan, ssl=np.nan, lh=np.nan, ll=np.nan, sh=np.nan, sl=np.nan)
    tmp, lv = {}, {}

    def levels(ep, d):
        if d > 0:
            risk = min(ep - S["lsl"], ep * 0.01)
            perc = (S["lh"] - S["ll"]) / S["ll"] * 100 if S["ll"] == S["ll"] else np.nan
            rr = 1 if perc > 1 else 2
            return ep - risk, ep + rr * risk
        risk = min(S["ssl"] - ep, ep * 0.01)
        perc = (S["sh"] - S["sl"]) / S["sl"] * 100 if S["sl"] == S["sl"] else np.nan
        rr = 1 if perc > 1 else 2
        return ep + risk, ep - rr * risk

    def orders(i, pos):
        out = []
        if buy[i] and pos == 0:
            S.update(lsl=l[i], lh=h[i], ll=l[i])
        if sell[i] and pos == 0:
            S.update(ssl=h[i], sh=h[i], sl=l[i])
        if buy[i]:
            out += [("close", -1), ("entry", 1)]
        if sell[i]:
            out += [("close", 1), ("entry", -1)]
        ep = tmp.get(i) if pos != 0 else None
        with np.errstate(invalid="ignore"):
            lv[i] = None if ep is None else (levels(ep, 1), levels(ep, -1))   # both exit orders use the same position_avg_price
        if ex_t[i] and pos != 0:
            out.append(("close", 1 if pos > 0 else -1))
        return out

    def stop(i, pos, ep, eb):
        tmp[i] = ep
        p = lv.get(i - 1) if i > 0 else None
        lev = None if p is None else p[0] if pos > 0 else p[1]
        if lev is None or np.isnan(lev[0]):
            return None
        return lev[0]

    def target(i, pos, ep, eb):
        p = lv.get(i - 1) if i > 0 else None
        lev = None if p is None else p[0] if pos > 0 else p[1]
        if lev is None or np.isnan(lev[1]):
            return None
        return lev[1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
