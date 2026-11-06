"""Independent check — DNSE VN301!, SMA ADX/DI Trend Following Strategy (ToaH6cKJ): 15-minute bars, New York time. SMA89 vs its value 5 bars ago (rising / falling, na -> false) with ADX(14) > 20 and +DI > -DI (-DI > +DI), entering on the first bar of the state, optionally filtered by the SMA200 slope; a flip of the SMA89 slope closes a position against it.
Entries reverse; only while minutes-of-day (bar start) lie in [09:00, 14:30); leaving the window closes any position at the next open. Once a position was open at a script run, stop = avg -/+ 10 and limit = avg +/- 20.0 work from the next bar.
Variants: default, trend filter without the time window, and no take-profit / long only / plain state."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_dmi, np_ema, np_rsi, np_sma, np_supertrend, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "ToaH6cKJ"


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


def one(df, params, use_tf, use_tp, direction, use_time=True, di=True, newonly=True):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    idx = np.arange(n)
    sma = np_sma(c, 200)
    prev = np.r_[np.nan, sma[:-1]]
    with np.errstate(invalid="ignore"):
        bull, bear = sma >= prev, sma < prev
    sh1 = lambda x: np.r_[False, x[:-1]]
    loc = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Asia/Ho_Chi_Minh")
    mins = (loc.dt.hour * 60 + loc.dt.minute).to_numpy()
    ins = (mins >= 540) & (mins < 870) if use_time else np.ones(n, bool)
    ended = ~ins & sh1(ins) & (idx > 0) if use_time else np.zeros(n, bool)
    s89 = np_sma(c, 89)
    p5 = np.r_[np.full(5, np.nan), s89[:-5]]
    pdi, mdi, adx = np_dmi(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        sup, sdn = s89 > p5, s89 < p5
        strong = adx > 20
        lstate = sup & strong & ((pdi > mdi) if di else True)
        sstate = sdn & strong & ((mdi > pdi) if di else True)
    gc = (lstate & ~sh1(lstate)) if newonly else lstate
    dc = (sstate & ~sh1(sstate)) if newonly else sstate
    fdn = sdn & sh1(sup) & (idx > 0)
    fup = sup & sh1(sdn) & (idx > 0)
    def orders(i, pos):
        out = []
        if fdn[i] and pos > 0:
            out.append(("close", 1))
        if fup[i] and pos < 0:
            out.append(("close", -1))
        if ended[i] and pos != 0:
            out.append(("close", pos))


        if gc[i] and (bull[i] if use_tf else True) and ins[i] and direction in ("Long", "Both"):
            out.append(("entry", 1))
        if dc[i] and (bear[i] if use_tf else True) and ins[i] and direction in ("Short", "Both"):
            out.append(("entry", -1))
        return out

    def level(i, pos, ep, eb, sgn):
        if eb >= i:
            return None
        return ep - pos * 10.0 if sgn < 0 else (ep + pos * 20.0 if use_tp else None)

    stop = lambda i, pos, ep, eb: level(i, pos, ep, eb, -1)
    tgt = lambda i, pos, ep, eb: level(i, pos, ep, eb, 1)
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt)
    sym = SymbolInfo.make("DNSE:VN301!", "stock", qty_step=1e-9, timezone="Asia/Ho_Chi_Minh", session="0900-1445")
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "commission_value": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(30000, seed=931, freq="15min")
    msgs, allok = [], True
    for params, tf, tp, dr, ut, di, no in (({}, False, True, "Both", True, True, True),
                                           ({"Use Time Filter?": False, "Use SMA Trend Filter?": True}, True, True, "Both", False, True, True),
                                           ({"Use Take Profit?": False, "Trade Direction": "Long", "Use DI Filter?": False, "Enter Only On New Signal?": False}, False, False, "Long", True, False, False)):
        ok, m = one(df, params, tf, tp, dr, ut, di, no)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
