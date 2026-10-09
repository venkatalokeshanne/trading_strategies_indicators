"""Independent check — SuperTrend Bot v6 [1H + ADX + SL] (02KcJZxe) on hourly bars.
Supertrend flips filtered by -DI (the original takes dmi's 2nd element) and by a 4H Supertrend
(lookahead_off: a 4H value reaches the chart on that 4H bar's last 1H bar). The exit is placed
only on a signal bar, from the average price BEFORE the new entry fills: na from flat, the old
position's price on a reversal, the position's own price when re-armed by a repeat signal."""
import numpy as np

from indep import bars, bracket_hit, compare, np_rma, np_supertrend, run_conversion

TV_ID = "02KcJZxe"


def minus_di(h, l, c, n):
    up, dn = np.r_[np.nan, np.diff(h)], -np.r_[np.nan, np.diff(l)]
    mdm = np.where(np.isnan(dn), np.nan, np.where((dn > up) & (dn > 0), dn, 0.0))
    pc = np.r_[np.nan, c[:-1]]
    tr = np.fmax(h - l, np.fmax(abs(h - pc), abs(l - pc)))
    tr[0] = np.nan
    with np.errstate(divide="ignore", invalid="ignore"):
        return 100 * np_rma(mdm, n) / np_rma(tr, n)


def check():
    df = bars(12000, seed=97, freq="h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    _, d = np_supertrend(h, l, c, 3.0, 10)
    mdi = minus_di(h, l, c, 14)
    grp = (df.time.to_numpy() // (4 * 3600 * 1000)).astype(np.int64)
    keys, first = np.unique(grp, return_index=True)
    last = np.r_[first[1:] - 1, n - 1]
    hh = np.maximum.reduceat(h, first)
    ll = np.minimum.reduceat(l, first)
    _, hd = np_supertrend(hh, ll, c[last], 3.0, 10)
    k_of = np.searchsorted(keys, grp)
    is_last = np.r_[grp[1:] != grp[:-1], True]
    htf = np.array([hd[k] if is_last[i] else (hd[k - 1] if k else np.nan) for i, k in enumerate(k_of)])

    adx_ok = mdi >= 20
    go_long = np.r_[False, (d[1:] == -1) & (d[:-1] == 1)] & adx_ok & (htf == -1)
    go_short = np.r_[False, (d[1:] == 1) & (d[:-1] == -1)] & adx_ok & (htf == 1)

    ref, pos, ep, eb, queued = [], 0, np.nan, -1, 0
    lv = {1: None, -1: None}                    # pending exit (stop, limit) per entry direction
    for i in range(n):
        if queued and queued != pos:
            if pos:
                ref.append((pos, eb, ep, i, o[i]))
                lv[pos] = None                  # its exit order goes with it
            pos, ep, eb = queued, o[i], i
        queued = 0
        if pos and lv[pos] is not None:
            hit = bracket_hit(o[i], h[i], l[i], c[i], pos, *lv[pos])
            if hit is not None:
                ref.append((pos, eb, ep, i, hit))
                lv[pos], pos = None, 0
        avg = ep if pos else np.nan
        if go_long[i]:
            queued = 1
            lv[1] = (avg * (1 - 0.015), avg * (1 + 0.03))
        if go_short[i]:
            queued = -1
            lv[-1] = (avg * (1 + 0.015), avg * (1 - 0.03))
    return compare(run_conversion(TV_ID, df, tf="60"), ref)
