"""Independent check — Gold Sniper (hOQRDd8y): hourly bars (24 h synthetic), market orders at the next open, one position at a time (entries are tried in source order, so two opposite signals of one bar reverse). Liquidity sweep: the prior bar's low (high) went under (over) the 30-bar extreme as it stood 3 bars ago and this bar closes back above (below) it and above (below) the previous close; stop = prior bar's low -/+ 0.5 x sweep depth, target = close +/- 2 x risk. RSI divergence: close under the lowest close of 10 bars as it stood 3 bars ago while RSI14 is above its own 10-bar low of that time and under 40 (mirrored over 60); stop 1 ATR14, target 1.5 ATR. All inside 08-20 UTC with at most 10 entries per weekday (counter reset when the weekday changes); the exit is attached at the entry and works from the fill bar; a position older than 20 (liq) / 15 (rsi) bars after its signal bar, or still open after the session, is closed at the next open. Uses the pending-order reference broker (simulate_ord). Commission / slippage off on the pinelib side.
Variants: defaults; liquidity sweep only with a 1.0 stop buffer; RSI scalp only, long only."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_rsi, run_conversion, simulate_ord

TV_ID = "hOQRDd8y"


def hi_n(x, n):
    return pd.Series(x).rolling(n).max().to_numpy()


def lo_n(x, n):
    return pd.Series(x).rolling(n).min().to_numpy()


def one(df, params, use_liq, use_rsi, slm, longs, shorts):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    t = pd.to_datetime(df["time"], unit="ms", utc=True)
    hr = t.dt.hour.to_numpy()
    dow = t.dt.dayofweek.to_numpy()
    rsi, atr = np_rsi(c, 14), np_atr(h, l, c, 14)
    sh = lambda x, k: np.r_[np.full(k, np.nan), x[:-k]]
    rh, rl = sh(hi_n(h, 30), 3), sh(lo_n(l, 30), 3)
    plow, rlow = sh(lo_n(c, 10), 3), sh(lo_n(rsi, 10), 3)
    phigh, rhigh = sh(hi_n(c, 10), 3), sh(hi_n(rsi, 10), 3)
    S = dict(dt=0, eb=0, act="")

    def orders(i, pos):
        out = []
        if i < 1:
            return out
        if i == 0 or dow[i] != dow[i - 1]:
            S["dt"] = 0
        sess = 8 <= hr[i] < 20
        ct = S["dt"] < 10
        with np.errstate(invalid="ignore"):
            bsw = l[i - 1] < rl[i] and c[i] > rl[i] and c[i] > c[i - 1]
            ssw = h[i - 1] > rh[i] and c[i] < rh[i] and c[i] < c[i - 1]
            bdp, sdp = rl[i] - l[i - 1], h[i - 1] - rh[i]
            bdv = c[i] < plow[i] and rsi[i] > rlow[i] and rsi[i] < 40
            sdv = c[i] > phigh[i] and rsi[i] < rhigh[i] and rsi[i] > 60
        lb = use_liq and bsw and bdp > 0 and sess and ct and longs
        ls = use_liq and ssw and sdp > 0 and sess and ct and shorts
        rb = use_rsi and bdv and sess and ct and longs
        rs = use_rsi and sdv and sess and ct and shorts
        nop = pos == 0
        if lb and nop:
            sl_ = l[i - 1] - bdp * slm
            out += [("entry", "Liq Long", 1, None, None), ("exit", "Liq Long TP/SL", "Liq Long", sl_, c[i] + (c[i] - sl_) * 2.0)]
            S.update(eb=i, act="liq")
            S["dt"] += 1
        if ls and nop:
            sl_ = h[i - 1] + sdp * slm
            out += [("entry", "Liq Short", -1, None, None), ("exit", "Liq Short TP/SL", "Liq Short", sl_, c[i] - (sl_ - c[i]) * 2.0)]
            S.update(eb=i, act="liq")
            S["dt"] += 1
        if rb and nop:
            out += [("entry", "RSI Long", 1, None, None), ("exit", "RSI Long TP/SL", "RSI Long", c[i] - atr[i], c[i] + atr[i] * 1.5)]
            S.update(eb=i, act="rsi")
            S["dt"] += 1
        if rs and nop:
            out += [("entry", "RSI Short", -1, None, None), ("exit", "RSI Short TP/SL", "RSI Short", c[i] + atr[i], c[i] - atr[i] * 1.5)]
            S.update(eb=i, act="rsi")
            S["dt"] += 1
        mb = 20 if S["act"] == "liq" else 15
        if pos != 0 and i - S["eb"] >= mb:
            out.append(("close_all",))
        if pos != 0 and not sess:
            out.append(("close_all",))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate_ord(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, tf="60", params=params, strategy_overrides={"slippage": 0, "commission_value": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(30000, seed=1301, freq="60min")
    for k in ("open", "high", "low", "close"):
        df[k] = 1800 * (df[k] / 100) ** 0.15
    msgs, allok = [], True
    cases = (({}, (True, True, 0.5, True, True)),
             ({"Enable RSI Divergence Scalp": False, "SL Buffer (× sweep depth)": 1.0}, (True, False, 1.0, True, True)),
             ({"Enable Liquidity Sweep Reversal": False, "Trade Direction": "Long Only"}, (False, True, 0.5, True, False)))
    for params, args in cases:
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
