"""Independent check — Shooting Star Reversal (0EIrk0Vm): 15-minute bars with prices x10 (so the 2.0 minimum body matters), short only, one position, market entry at the next open. Signal: body >= 2.0, upper wick >= 3 x body, lower wick < 1 x body,
close above the close 5 bars back (and, in the session variant, bar-start hour in [7, 20) New York). Stop = signal high + 0.5 body, target = signal close - 3 body, placed with the entry (work from the fill bar). Slippage / margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "0EIrk0Vm"


def one(df, params, sess):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    body = np.abs(c - o)
    uw = h - np.fmax(o, c)
    lw = np.fmin(o, c) - l
    hour = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York").dt.hour.to_numpy()
    c5 = np.r_[np.full(5, np.nan), c[:-5]]
    with np.errstate(invalid="ignore"):
        sig = (body >= 2.0) & (uw >= body * 3.0) & (lw < body) & (c > c5)
        if sess:
            sig &= (hour >= 7) & (hour < 20)
    lev = {}

    def orders(i, pos):
        if pos == 0 and sig[i]:
            lev[i] = (h[i] + body[i] * 0.5, c[i] - body[i] * 3.0)
            return [("entry", -1)]
        return []

    stop = lambda i, pos, ep, eb: lev[eb - 1][0] if eb - 1 in lev else None
    tgt = lambda i, pos, ep, eb: lev[eb - 1][1] if eb - 1 in lev else None
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt)
    sym = SymbolInfo.make("OANDA:XAUUSD", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(30000, seed=621, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = df[k] * 10.0
    msgs, allok = [], True
    for params, sess in (({}, False), ({"Only trade during session?": True}, True)):
        ok, m = one(df, params, sess)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
