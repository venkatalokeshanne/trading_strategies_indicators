"""Independent check — SuperTrend + EMA [BTC-USD] (sNFXyA3m), chart-timeframe SuperTrend (blank input).
The old close[1]-band SuperTrend is rebuilt in numpy; the security call (lookahead on, chart TF) returns the previous bar's
up/dn/trend. Entries/closes fire at the next open; one contract, pyramiding 0 (a repeated entry is ignored, an opposite
entry reverses)."""
import numpy as np

from indep import (bars, compare_q, np_atr, np_dmi, np_ema, np_cross_over, np_cross_under, run_conversion,
                   simulate_brackets)

TV_ID = "sNFXyA3m"


def supertrend_old(h, l, c, factor, n):
    hl2 = (h + l) / 2
    atr = np_atr(h, l, c, n)
    N = len(c)
    up, dn, tr = np.full(N, np.nan), np.full(N, np.nan), np.full(N, np.nan)
    for i in range(N):
        u = hl2[i] - factor * atr[i]
        d = hl2[i] + factor * atr[i]
        u1 = up[i - 1] if i and not np.isnan(up[i - 1]) else u
        d1 = dn[i - 1] if i and not np.isnan(dn[i - 1]) else d
        if i and c[i - 1] > u1:
            u = max(u, u1)
        if i and c[i - 1] < d1:
            d = min(d, d1)
        t = tr[i - 1] if i and not np.isnan(tr[i - 1]) else 1
        if t == -1 and c[i] > d1:
            t = 1
        elif t == 1 and c[i] < u1:
            t = -1
        up[i], dn[i], tr[i] = u, d, t
    return np.r_[np.nan, tr[:-1]]


def check():
    df = bars(9000, seed=21, freq="h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    trend = supertrend_old(h, l, c, 3.0, 10)
    prev = np.r_[np.nan, trend[:-1]]
    flip_buy = (trend == 1) & (prev == -1)
    flip_sell = (trend == -1) & (prev == 1)
    e50, e200 = np_ema(c, 50), np_ema(c, 200)
    adx = np_dmi(h, l, c, 14)[2]
    with np.errstate(divide="ignore", invalid="ignore"):
        sep = np.abs(e50 - e200) / e200 * 100
        tr1 = np_atr(h, l, c, 1)
        s = np.full(n, np.nan)
        hh = np.full(n, np.nan)
        ll = np.full(n, np.nan)
        for i in range(13, n):
            s[i] = tr1[i - 13:i + 1].sum()
            hh[i] = h[i - 13:i + 1].max()
            ll[i] = l[i - 13:i + 1].min()
        rng = hh - ll
        chop = np.where(rng > 0, 100.0 * np.log10(s / rng) / np.log10(14), 50.0)
    trending = (adx >= 20) & (sep >= 0.5) & (chop <= 61.8)
    cb, cs = np_cross_over(e50, e200), np_cross_under(e50, e200)
    fresh_buy = ((flip_buy & (e50 > e200)) | (cb & (trend == 1))) & trending
    fresh_sell = ((flip_sell & (e50 < e200)) | (cs & (trend == -1))) & trending
    def orders(i, info):
        acts = []
        if flip_sell[i]:
            acts.append(("close", "Long"))
        if flip_buy[i]:
            acts.append(("close", "Short"))
        if fresh_buy[i]:
            acts.append(("entry", "Long", 1, 1))
        if fresh_sell[i]:
            acts.append(("entry", "Short", -1, 1))
        return acts

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1)
    return compare_q(run_conversion(TV_ID, df, tf="60"), ref)
