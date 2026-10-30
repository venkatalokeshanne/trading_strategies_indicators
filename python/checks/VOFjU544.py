"""Independent check — GXG Trend Engine (VOFjU544): daily bars, long only. ATR(1) = true range (na on the first bar); trail = UT-Bot recursion with nz(prev, 0) and a 3 x ATR buffer; EMA(feed, 1) = feed. The feed crossing over the trail
buys, the trail crossing over the feed closes the long. Run with the plain close feed and with the Heikin Ashi option (HA close = (o+h+l+c)/4). Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_cross_over, np_tr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "VOFjU544"


def trail_line(feed, buf):
    n = len(feed)
    t = np.zeros(n)
    prev = 0.0
    for i in range(n):
        p, p1 = feed[i], (feed[i - 1] if i else np.nan)
        if p > prev and p1 > prev:
            t[i] = np.nan if np.isnan(buf[i]) else max(prev, p - buf[i])
        elif p < prev and p1 < prev:
            t[i] = np.nan if np.isnan(buf[i]) else min(prev, p + buf[i])
        elif p > prev:
            t[i] = p - buf[i]
        else:
            t[i] = p + buf[i]
        prev = 0.0 if np.isnan(t[i]) else t[i]
    return t


def check():
    df = bars(6000, seed=291)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    buf = 3.0 * np_tr(h, l, c, False)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    msgs, ok_all = [], True
    for ha in (False, True):
        feed = (o + h + l + c) / 4 if ha else c
        t = trail_line(feed, buf)
        with np.errstate(invalid="ignore"):
            bull, bear = np_cross_over(feed, t), np_cross_over(t, feed)
            ls, ss = (feed > t) & bull, (feed < t) & bear
        ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if ls[i] else []) + ([("close", 1)] if ss[i] and pos > 0 else []))
        ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Use Heikin Ashi Source": ha},
                                            strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
        ok_all = ok_all and ok and len(ref) > 10
        msgs.append(f"HA {'on' if ha else 'off'}: {detail} ({len(ref)})")
    return ok_all, "; ".join(msgs)
