"""Independent check — Sequence Snap (49jNhJXM): hourly bars (returns compressed 3x so runs form), one position, market entries at the next open. Long: the bar N back (N = 2..5) was a red candle; every one of the last N bars is green, trades above the reversal candle's low and (all but the oldest of the run) closes above the previous close x (1 - 0.05 %); RSI14 > 40 and rising.
Short mirrored (off by default). Stop = reversal candle low (high), target = close + 1.5 x (close - stop), set at the signal; the bracket is issued from the first script run that sees the position (works from the next bar). Variants: N = 5 default; N = 3 with shorts allowed and a 1R target; N = 2 with RSI filter off. Slippage / margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "49jNhJXM"


def one(df, params, N, shorts, rr, use_rsi):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    rsi = np_rsi(c, 14)
    prsi = np.r_[np.nan, rsi[:-1]]
    with np.errstate(invalid="ignore"):
        rok_l = (rsi > 40) & (rsi > prsi) if use_rsi else np.ones(n, bool)
        rok_s = (rsi < 60) & (rsi < prsi) if use_rsi else np.ones(n, bool)
    tol = 0.05
    S = dict(sl=np.nan, tp=np.nan)
    poscl = np.zeros(n)
    sl_arr, tp_arr = np.full(n, np.nan), np.full(n, np.nan)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if i >= N:
            bull = True
            bear = True
            for k in range(N):
                a = i - k
                if c[a] <= o[a] or l[a] <= l[i - N]:
                    bull = False
                if c[a] >= o[a] or h[a] >= h[i - N]:
                    bear = False
                if k < N - 1:
                    if c[a] <= c[a - 1] * (1 - tol / 100):
                        bull = False
                    if c[a] >= c[a - 1] * (1 + tol / 100):
                        bear = False
            ls = (c[i - N] < o[i - N]) and bull and bool(rok_l[i])
            ss = (c[i - N] > o[i - N]) and bear and bool(rok_s[i])
            if ls and pos == 0:
                S["sl"] = l[i - N]
                S["tp"] = c[i] + (c[i] - S["sl"]) * rr
                out.append(("entry", 1))
            if shorts and ss and pos == 0:
                S["sl"] = h[i - N]
                S["tp"] = c[i] - (S["sl"] - c[i]) * rr
                out.append(("entry", -1))
        if pos != 0 and not np.isnan(S["sl"]):
            sl_arr[i], tp_arr[i] = S["sl"], S["tp"]
        return out

    def lvl(arr):
        return lambda i, pos, ep, eb: None if (i == 0 or eb >= i or poscl[i - 1] * pos <= 0 or np.isnan(arr[i - 1])) else arr[i - 1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lvl(sl_arr), target=lvl(tp_arr))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(60000, seed=771, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100.0 * (df[k] / 100.0) ** (1 / 3)
    msgs, allok = [], True
    for params, N, sh, rr, ur in (({}, 5, False, 1.5, True), ({"Candles In The Run": 3, "Allow Shorts": True, "Reward Target": "1R"}, 3, True, 1.0, True),
                                  ({"Candles In The Run": 2, "Require RSI Agreement": False}, 2, False, 1.5, False)):
        ok, m = one(df, params, N, sh, rr, ur)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
