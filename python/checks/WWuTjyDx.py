"""Independent check — Capitulation Stretch Reversion (WWuTjyDx): daily bars, one position, market orders at the next open. Setup: close above EMA200, close < EMA5 - 0.5 ATR14, >= 2 consecutive lower closes (run counter reset by any non-lower close), up candle -> long; shorts
(Trade Shorts on): close below EMA200, close > EMA5 + 0.5 ATR, >= 2 consecutive higher closes, down candle. Stop = signal close -/+ 3 ATR, issued from the first script run that sees the position (so it works from the bar after the fill); bars-held counter starts at 0 on the signal and is
incremented at every script run with a position; the close is at/over the mean (<= for shorts) -> close at the next open, else after 10 bars. Variants: longs only, longs and shorts. Slippage / margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "WWuTjyDx"


def one(df, params, shorts):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    mean, trend, atr = np_ema(c, 5), np_ema(c, 200), np_atr(h, l, c, 14)
    dr, ur = np.zeros(n, int), np.zeros(n, int)
    for i in range(1, n):
        dr[i] = dr[i - 1] + 1 if c[i] < c[i - 1] else 0
        ur[i] = ur[i - 1] + 1 if c[i] > c[i - 1] else 0
    with np.errstate(invalid="ignore"):
        lsu = (c > trend) & (c < mean - 0.5 * atr) & (dr >= 2) & (c > o)
        ssu = shorts & (c < trend) & (c > mean + 0.5 * atr) & (ur >= 2) & (c < o)
    S = dict(stop=np.nan, bh=0)
    stop_arr = np.full(n, np.nan)

    def orders(i, pos):
        out = []
        if pos == 0 and lsu[i]:
            out.append(("entry", 1))
            S["stop"], S["bh"] = c[i] - 3.0 * atr[i], 0
        elif pos == 0 and ssu[i]:
            out.append(("entry", -1))
            S["stop"], S["bh"] = c[i] + 3.0 * atr[i], 0
        if pos != 0:
            S["bh"] += 1
            if not np.isnan(S["stop"]):
                stop_arr[i] = S["stop"]
            if (pos > 0 and c[i] >= mean[i]) or (pos < 0 and c[i] <= mean[i]) or S["bh"] >= 10:
                out.append(("close", pos))
        return out

    stop = lambda i, pos, ep, eb: None if (eb >= i or np.isnan(stop_arr[i - 1])) else stop_arr[i - 1]
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(14000, seed=591)
    msgs, allok = [], True
    for params, sh in (({}, False), ({"Trade Shorts": True}, True)):
        ok, m = one(df, params, sh)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
