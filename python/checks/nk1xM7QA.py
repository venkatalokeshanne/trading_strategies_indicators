"""Independent check — CNPS 01 MACD (nk1xM7QA): 15-minute bars, New York time. MACD(12,26,9) crosses open a long / short (reversing), filtered by the SMA200 slope (>= previous long, < previous short, na -> false); only
while minutes-of-day (bar start) lie in [09:00, 14:30). Leaving the window closes any position at the next open. Once a position was open at a script run, stop = avg -/+ 10 and limit = avg +/- 30 work from the next bar.
Variants: default, and no trend filter / no take-profit / long only."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "nk1xM7QA"


def one(df, params, use_tf, use_tp, direction):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    macd = np_ema(c, 12) - np_ema(c, 26)
    sig = np_ema(macd, 9)
    gc, dc = np_cross_over(macd, sig), np_cross_under(macd, sig)
    sma = np_sma(c, 200)
    prev = np.r_[np.nan, sma[:-1]]
    with np.errstate(invalid="ignore"):
        bull, bear = sma >= prev, sma < prev
    loc = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (loc.dt.hour * 60 + loc.dt.minute).to_numpy()
    ins = (mins >= 540) & (mins < 870)
    pins = np.r_[False, ins[:-1]]
    ended = ~ins & pins & (np.arange(n) > 0)
    poscl = np.zeros(n)

    def orders(i, pos):
        poscl[i] = pos
        out = []
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
        return ep + sgn * pos * 10.0 if sgn < 0 else (ep + pos * 30.0 if use_tp else None)

    stop = lambda i, pos, ep, eb: level(i, pos, ep, eb, -1)
    tgt = lambda i, pos, ep, eb: level(i, pos, ep, eb, 1)
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(30000, seed=411, freq="15min")
    msgs, allok = [], True
    for params, tf, tp, dr in (({}, True, True, "Cả hai"),
                               ({"Dùng bộ lọc xu hướng SMA?": False, "Dùng chốt lời?": False, "Chiều giao dịch": "Mua"}, False, False, "Mua")):
        ok, m = one(df, params, tf, tp, dr)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
