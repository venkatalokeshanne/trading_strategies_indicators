"""Independent check — CNPS10 - SMA/PSAR (qlWWDZOI): 15-minute bars, New York time. SMA14 slope (> / < previous) with the close above / below Wilder's parabolic SAR (0.02, 0.02, 0.2; Pine's reference algorithm) opens long / short; the position is closed when the SMA turns against it or the close is no longer on its side of the SAR (a na SAR counts as 'not above / below').
Entries reverse; only while minutes-of-day (bar start) lie in [09:00, 14:30); leaving the window closes any position at the next open. Once a position was open at a script run, stop = avg -/+ 10 and limit = avg +/- 30.0 work from the next bar.
Variants: default, no time window, and no take-profit / long only."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_dmi, np_ema, np_rsi, np_sma, np_supertrend, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "qlWWDZOI"


def np_sar(h, l, c, start, inc, mx):
    """Parabolic SAR exactly as in the Pine reference implementation (docs: ta.sar)."""
    n = len(c)
    out = np.full(n, np.nan)
    result = maxmin = acc = np.nan
    below = False
    for i in range(n):
        first = False
        if i == 1:
            if c[1] > c[0]:
                below, maxmin, result = True, h[1], l[0]
            else:
                below, maxmin, result = False, l[1], h[0]
            first, acc = True, start
        if i >= 1:
            result = result + acc * (maxmin - result)
            if below:
                if result > l[i]:
                    first, below, result, maxmin, acc = True, False, max(h[i], maxmin), l[i], start
            elif result < h[i]:
                first, below, result, maxmin, acc = True, True, min(l[i], maxmin), h[i], start
            if not first:
                if below and h[i] > maxmin:
                    maxmin, acc = h[i], min(acc + inc, mx)
                elif not below and l[i] < maxmin:
                    maxmin, acc = l[i], min(acc + inc, mx)
            if below:
                result = min(result, l[i - 1])
                if i > 1:
                    result = min(result, l[i - 2])
            else:
                result = max(result, h[i - 1])
                if i > 1:
                    result = max(result, h[i - 2])
            out[i] = result
    return out


def pstd(c, n):
    return pd.Series(c).rolling(n, min_periods=n).std(ddof=0).to_numpy()


def one(df, params, use_tf, use_tp, direction, use_time=True):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    idx = np.arange(n)
    sh1 = lambda x: np.r_[False, x[:-1]]
    loc = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (loc.dt.hour * 60 + loc.dt.minute).to_numpy()
    ins = (mins >= 540) & (mins < 870) if use_time else np.ones(n, bool)
    ended = ~ins & sh1(ins) & (idx > 0) if use_time else np.zeros(n, bool)
    s14 = np_sma(c, 14)
    p14 = np.r_[np.nan, s14[:-1]]
    ps = np_sar(h, l, c, 0.02, 0.02, 0.2)
    with np.errstate(invalid="ignore"):
        sup, sdn = s14 > p14, s14 < p14
        ab, be = c > ps, c < ps
        gc, dc = sup & ab, sdn & be
        xl, xs = sdn | ~ab, sup | ~be
    fdn = fup = np.zeros(n, bool)
    def orders(i, pos):
        out = []
        if fdn[i] and pos > 0:
            out.append(("close", 1))
        if fup[i] and pos < 0:
            out.append(("close", -1))
        if ended[i] and pos != 0:
            out.append(("close", pos))
        if pos > 0 and xl[i]:
            out.append(("close", 1))
        if pos < 0 and xs[i]:
            out.append(("close", -1))

        if gc[i] and (True) and ins[i] and direction in ("Mua", "Cả hai"):
            out.append(("entry", 1))
        if dc[i] and (True) and ins[i] and direction in ("Bán", "Cả hai"):
            out.append(("entry", -1))
        return out

    def level(i, pos, ep, eb, sgn):
        if eb >= i:
            return None
        return ep - pos * 10.0 if sgn < 0 else (ep + pos * 30.0 if use_tp else None)

    stop = lambda i, pos, ep, eb: level(i, pos, ep, eb, -1)
    tgt = lambda i, pos, ep, eb: level(i, pos, ep, eb, 1)
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(30000, seed=522, freq="15min")
    msgs, allok = [], True
    for params, tf, tp, dr, ut in ((({}, False, True, "Cả hai", True), ({"Dùng bộ lọc giờ?": False}, False, True, "Cả hai", False), ({"Dùng chốt lời?": False, "Chiều giao dịch": "Mua"}, False, False, "Mua", True))):
        ok, m = one(df, params, tf, tp, dr, ut)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
