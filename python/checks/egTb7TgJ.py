"""Independent check — Gaussian Channel ETH (egTb7TgJ): hourly bars on a crypto symbol (UTC clock), long only, market entries / closes at the next open. DonovanWall's Gaussian filter, 4 poles, sampling period 144: beta = (1 - cos(2 pi / 144)) / (1.414^(2/4) - 1), alpha = -beta + sqrt(beta^2 + 2 beta), and the 4-pole recursion
f = a^4 s + 4 x f[1] - 6 x^2 f[2] + 4 x^3 f[3] - x^4 f[4] (x = 1 - alpha, nz() on the past values and the source) applied to hlc3 and to the true range; bands = filter +/- 1.414 x filtered TR. Entry (flat, from 2018-01-01): the filter rose, the close is above the upper band, stochastic-RSI %K (SMA3 of stoch(RSI14, 14)) > 80 or < 15.
Exit: close < upper band or the filter fell. Stop = lower band, issued from the first script run that sees the position. Defaults here: period 89, multiplier 1.5, lower threshold 25, bullish-candle filter and the 200-SMA gate on, start 2020. Variants: defaults, and a 60 period without gate / candle filter. Margin / slippage off on the pinelib side."""
import math

import numpy as np

from indep import bars, compare, np_rsi, np_sma, np_stoch, np_tr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "egTb7TgJ"


def filt4(a, s, n=4):
    out = np.zeros(len(s))
    x = 1 - a
    m2 = {4: 6, 1: 0}.get(n, 0)
    m3 = {4: 4}.get(n, 0)
    m4 = {4: 1}.get(n, 0)

    def g(t, k):
        return out[t - k] if t - k >= 0 else 0.0

    for t in range(len(s)):
        nzs = 0.0 if np.isnan(s[t]) else s[t]
        out[t] = (math.pow(a, n) * nzs + n * x * g(t, 1) - (m2 * math.pow(x, 2) * g(t, 2) if n >= 2 else 0) + (m3 * math.pow(x, 3) * g(t, 3) if n >= 3 else 0)
                  - (m4 * math.pow(x, 4) * g(t, 4) if n >= 4 else 0))
    return out


def channel(h, l, c, per, mult):
    n = 4
    beta = (1 - math.cos(4 * math.asin(1) / per)) / (math.pow(1.414, 2 / n) - 1)
    alpha = -beta + math.sqrt(math.pow(beta, 2) + 2 * beta)
    src = (h + l + c) / 3
    tr = np_tr(h, l, c, True)
    filt, ftr = filt4(alpha, src), filt4(alpha, tr)
    return filt, filt + ftr * mult, filt - ftr * mult


def one(df, params, per, mult, lower, bullish, start, regime=True):
    o, h, l, c, t = (df[k].to_numpy() for k in ("open", "high", "low", "close", "time"))
    n = len(c)
    filt, hband, lband = channel(h, l, c, per, mult)
    rsi = np_rsi(c, 14)
    k = np_sma(np_stoch(rsi, rsi, rsi, 14), 3)
    pf = np.r_[np.nan, filt[:-1]]
    t0 = int(np.datetime64(f"{start}-01-01T00:00:00", "ms").astype("int64"))
    with np.errstate(invalid="ignore"):
        long_c = (filt > pf) & ((c > np_sma(c, 200)) if regime else True) & (c > hband * (1 + 0.0 / 100)) & ((k > 80) | (k < lower)) & ((c > o) if bullish else True) & (t >= t0)
        close_c = ((c < hband) | (filt < pf)) & (t >= t0)
    poscl = np.zeros(n)
    stop_arr = np.full(n, np.nan)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if long_c[i] and pos == 0:
            out.append(("entry", 1))
        if close_c[i] and pos > 0:
            out.append(("close", 1))
        if pos > 0:
            stop_arr[i] = lband[i]
        return out

    stop = lambda i, pos, ep, eb: None if (i == 0 or eb >= i or poscl[i - 1] <= 0 or np.isnan(stop_arr[i - 1])) else stop_arr[i - 1]
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop)
    sym = SymbolInfo.make("BINANCE:BTCUSD", "crypto", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(60000, seed=942, freq="1h")
    msgs, allok = [], True
    for params, per, mult, lower, bull, start, reg in (({}, 89, 1.5, 25, True, 2020, True),
                                                       ({"Sampling Period": 60, "RSI Lower Threshold (Oversold)": 40, "Require bullish (green) entry candle": False, "Start year": 2016,
                                                         "Enable 200-SMA bull-market gate": False}, 60, 1.5, 40, False, 2016, False)):
        ok, m = one(df, params, per, mult, lower, bull, start, reg)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
