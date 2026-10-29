"""Independent check — Momentum Sequence Strategy [Herman] (mmrInMTp): daily bars, one position, market entries at the next open. Long setup: the main candle (N bars back) is bearish, and each of the last N bars is bullish, closes above the previous bar's close and has a low above the main candle's low; stop = main low, target = close + R x (close - stop); the exit is only issued once the position exists, so it works from the bar after the entry fill (the fill bar itself has no exit). Short mirrored. Margin, slippage, commission off on the pinelib side. Variants: N=5/1.5R long only, N=3/1R both, N=2/2R short only."""
import numpy as np

from indep import bars, compare, run_conversion, simulate

TV_ID = "mmrInMTp"


def one(df, params, fc, rr, lng, sht):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    lev = {}

    def orders(i, pos):
        if i < fc:
            return []
        bull = c[i - fc] > o[i - fc]
        bear = c[i - fc] < o[i - fc]
        vb = all(c[i - k] > o[i - k] and l[i - k] > l[i - fc] for k in range(fc)) and all(c[i - k] > c[i - k - 1] for k in range(fc - 1))
        vs = all(c[i - k] < o[i - k] and h[i - k] < h[i - fc] for k in range(fc)) and all(c[i - k] < c[i - k - 1] for k in range(fc - 1))
        out = []
        if lng and bear and vb and pos == 0:
            lev[i] = (l[i - fc], c[i] + (c[i] - l[i - fc]) * rr)
            out.append(("entry", 1))
        if sht and bull and vs and pos == 0:
            lev[i] = (h[i - fc], c[i] - (h[i - fc] - c[i]) * rr)
            out.append(("entry", -1))
        return out

    stop = lambda i, pos, ep, eb: lev[eb - 1][0] if i > eb and eb - 1 in lev else None
    tgt = lambda i, pos, ep, eb: lev[eb - 1][1] if i > eb and eb - 1 in lev else None
    ref = simulate(o, h, l, c, orders, stop=stop, target=tgt)
    ok, d = compare(run_conversion(TV_ID, df, params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "commission_value": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(6000, seed=77)
    msgs, allok = [], True
    for params, args in (({}, (5, 1.5, True, False)),
                         ({"Following Candles": 3, "Take Profit": "1R", "Short Trades": True}, (3, 1.0, True, True)),
                         ({"Following Candles": 2, "Take Profit": "2R", "Long Trades": False, "Short Trades": True}, (2, 2.0, False, True))):
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
