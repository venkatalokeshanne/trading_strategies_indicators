"""Independent check — CNPS5 - SMA / ADX (dg3LhrbJ): 15-minute bars, New York time. Signal SMA20 slope (>= previous rising / < previous falling) with ADX(14) > 25 opens long / short, filtered by the SMA200 slope; a flip of the SMA20 slope closes a position against it.
Entries reverse; only while minutes-of-day (bar start) lie in [09:00, 14:30); leaving the window closes any position at the next open. Once a position was open at a script run, stop = avg -/+ 10 and limit = avg +/- 20.0 work from the next bar.
Variants: default, no time window, and no trend filter / no take-profit / long only."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_dmi, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "dg3LhrbJ"


def pstd(c, n):
    return pd.Series(c).rolling(n, min_periods=n).std(ddof=0).to_numpy()


def one(df, params, use_tf, use_tp, direction, use_time=True):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    idx = np.arange(n)
    sma = np_sma(c, 200)
    prev = np.r_[np.nan, sma[:-1]]
    with np.errstate(invalid="ignore"):
        bull, bear = sma >= prev, sma < prev
    sh1 = lambda x: np.r_[False, x[:-1]]
    loc = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (loc.dt.hour * 60 + loc.dt.minute).to_numpy()
    ins = (mins >= 540) & (mins < 870) if use_time else np.ones(n, bool)
    ended = ~ins & sh1(ins) & (idx > 0) if use_time else np.zeros(n, bool)
    s20 = np_sma(c, 20)
    p20 = np.r_[np.nan, s20[:-1]]
    adx = np_dmi(h, l, c, 14)[2]
    with np.errstate(invalid="ignore"):
        sup, sdn = s20 >= p20, s20 < p20
        strong = adx > 25
    gc, dc = sup & strong, sdn & strong
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

        if gc[i] and (bull[i] if use_tf else True) and ins[i] and direction in ("Mua", "Cả hai"):
            out.append(("entry", 1))
        if dc[i] and (bear[i] if use_tf else True) and ins[i] and direction in ("Bán", "Cả hai"):
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
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(30000, seed=512, freq="15min")
    msgs, allok = [], True
    for params, tf, tp, dr, ut in ((({}, True, True, "Cả hai", True), ({"Dùng bộ lọc giờ?": False}, True, True, "Cả hai", False), ({"Dùng bộ lọc xu hướng SMA?": False, "Dùng chốt lời?": False, "Chiều giao dịch": "Mua"}, False, False, "Mua", True))):
        ok, m = one(df, params, tf, tp, dr, ut)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
