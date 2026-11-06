"""Independent check — 20 / 200 SMA Strategy (ZqnuKIAw): daily bars, one position, orders processed on the signal bar's close, bracket placed with the entry. A 20 / 200 SMA cross arms a side (the opposite side is disarmed; arming expires after 100 bars and is consumed by an entry); entry modes: armed + close beyond the 20 SMA, fast/slow trend + close crossing the 20 SMA, or trend + close beyond the 20 SMA. Stop: the low (or body edge) of the last bar that was an opposing candle beyond the 200 SMA within the lookback, minus a buffer (falls back to a fixed distance when missing or on the wrong side), fixed distance, or recent swing; target a fixed number of points. Variants: default, original cross + slope/colour/distance filters, relaxed + fixed stop (sell only), pullback + swing stop with body edges."""
import numpy as np

from indep import bars, compare, np_sma, run_conversion, simulate

TV_ID = "ZqnuKIAw"


def one(df, params, mode, sdir, stopm, wick, slope, color, dist):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    tp, fixed, buf, lookb, swing, maxd, win = 8.0, 5.0, 1.0, 300, 10, 6.0, 100
    f, s = np_sma(c, 20), np_sma(c, 200)
    sh = lambda x, k=1: np.r_[np.full(k, np.nan), x[:-k]]
    with np.errstate(invalid="ignore"):
        pf, ps, pc = sh(f), sh(s), sh(c)
        bullx = (f > s) & (pf <= ps)
        bearx = (f < s) & (pf >= ps)
        pb_up = (c > f) & (pc <= pf)
        pb_dn = (c < f) & (pc >= pf)
        fa, fb = f > s, f < s
        rising, falling = s > sh(s, 5), s < sh(s, 5)
        buyopp = (c < o) & (c < s)
        sellopp = (c > o) & (c > s)
    lo_s = np.array([l[max(0, i - swing + 1):i + 1].min() if i >= swing - 1 else np.nan for i in range(n)])
    hi_s = np.array([h[max(0, i - swing + 1):i + 1].max() if i >= swing - 1 else np.nan for i in range(n)])
    # barssince / valuewhen
    buy_bs, sell_bs = np.full(n, np.nan), np.full(n, np.nan)
    buy_v, sell_v = np.full(n, np.nan), np.full(n, np.nan)
    lb = ls = -1
    for i in range(n):
        if buyopp[i]:
            lb = i
        if sellopp[i]:
            ls = i
        if lb >= 0:
            buy_bs[i] = i - lb
            buy_v[i] = l[lb] if wick else min(o[lb], c[lb])
        if ls >= 0:
            sell_bs[i] = i - ls
            sell_v[i] = h[ls] if wick else max(o[ls], c[ls])
    S = dict(la=False, sa=False, lc=-1, sc=-1)
    lev = {}

    def orders(i, pos):
        if bullx[i]:
            S.update(la=True, sa=False, lc=i)
        if bearx[i]:
            S.update(sa=True, la=False, sc=i)
        lwin = S["la"] and i - S["lc"] <= win
        swin = S["sa"] and i - S["sc"] <= win
        if mode == 0:
            bl, bs_ = lwin and c[i] > f[i], swin and c[i] < f[i]
        elif mode == 1:
            bl, bs_ = fa[i] and pb_up[i], fb[i] and pb_dn[i]
        else:
            bl, bs_ = fa[i] and c[i] > f[i], fb[i] and c[i] < f[i]
        okl = (not slope or rising[i]) and (not color or c[i] > o[i]) and (not dist or abs(c[i] - f[i]) <= maxd)
        oks = (not slope or falling[i]) and (not color or c[i] < o[i]) and (not dist or abs(c[i] - f[i]) <= maxd)
        ls_sig = sdir in (0, 1) and bl and okl and pos == 0
        ss_sig = sdir in (0, 2) and bs_ and oks and pos == 0
        if np.isnan(f[i]) or np.isnan(s[i]):
            ls_sig = ss_sig = False
        lo_ = buy_v[i] if buy_bs[i] <= lookb else np.nan
        so_ = sell_v[i] if sell_bs[i] <= lookb else np.nan
        lfix, sfix = c[i] - fixed, c[i] + fixed
        if stopm == 0:
            sl_, ss_ = lo_ - buf, so_ + buf
        elif stopm == 1:
            sl_, ss_ = lfix, sfix
        else:
            sl_, ss_ = lo_s[i] - buf, hi_s[i] + buf
        fl = sl_ if (not np.isnan(sl_) and sl_ < c[i]) else lfix
        fs = ss_ if (not np.isnan(ss_) and ss_ > c[i]) else sfix
        out = []
        if ls_sig:
            out.append(("entry", 1))
            lev[i] = (fl, c[i] + tp)
            S["la"] = False
        if ss_sig:
            out.append(("entry", -1))
            lev[i] = (fs, c[i] - tp)
            S["sa"] = False
        return out

    stop = lambda i, pos, ep, eb: lev[eb][0] if eb in lev else None
    tgt = lambda i, pos, ep, eb: lev[eb][1] if eb in lev else None
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt, on_close=True)
    ok, d = compare(run_conversion(TV_ID, df, params=params, strategy_overrides={}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(3000, seed=33)
    msgs, allok = [], True
    cases = (
        ({}, 1, 0, 0, True, False, False, False),
        ({"Entry Strictness": "Original Cross Entry", "Use 200 SMA Slope Filter": True, "Use Candle Color Filter": True,
          "Avoid Entries Too Far From 20 SMA": True}, 0, 0, 0, True, True, True, False),
        ({"Entry Strictness": "Relaxed Testing Entry", "Stop Loss Method": "Fixed Points", "Trade Direction": "Sell Only"}, 2, 2, 1, True, False, False, False),
        ({"Stop Loss Method": "Recent Swing", "Opposing Candle Stop Uses Wick": False}, 1, 0, 2, False, False, False, False),
    )
    for params, mode, sdir, stopm, wick, slope, color, dist in cases:
        params = dict(params)
        params.update({"Take Profit Points": 8.0, "Fixed / Fallback Stop Points": 5.0, "Max Distance From 20 SMA": 6.0})
        ok, m = one(df, params, mode, sdir, stopm, wick, slope, color, params.get("Avoid Entries Too Far From 20 SMA", False))
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
