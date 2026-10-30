"""Independent check — Z-Score Mean Reversion Pro (92rilzXd): daily bars, market orders at the next open, pyramiding 1 (a same-side entry is ignored but still restarts the cooldown counters). z = (close - SMA80) / sample stdev(80) (0 if the deviation is 0); long: z < -threshold, RSI14 < 30, Bollinger (20, 2) width / basis > 0.02, close > EMA200; short mirrored. Per side cooldown (the counter starts at the cooldown value, +1 each bar, a signal of one side resets its own counter to 0 and the other to the cooldown); an opposite position is closed before the entry. The ATR stop (2) / target (3) are set from the CLOSE of the bar where the position size first becomes non-zero from zero (not on a reversal, which keeps the old levels) and the exit is re-issued every bar while the position is open, so it works from the bar after the fill and only for the position's own direction. With ATR exits off the position is closed on z beyond the exit threshold (long z > 0.5) or z crossing zero. Commission off on the pinelib side.
Variants: defaults with looser filters (z 1.5, RSI filter off, BB filter off, cooldown 3), z 2.0 with ATR exits off, EMA filter off with z 1.8."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_rsi, np_sma, run_conversion, simulate

TV_ID = "92rilzXd"


def one(df, params, zt, rsif, bbf, emaf, cd, atrx, zx=0.5):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    s = pd.Series(c)
    mean, sd = np_sma(c, 80), s.rolling(80).std(ddof=1).to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        z = np.where(sd > 0, (c - mean) / sd, 0.0)
    rsi = np_rsi(c, 14)
    bm = np_sma(c, 20)
    bd = 2.0 * s.rolling(20).std(ddof=0).to_numpy()
    bw = np.where(bm > 0, 2 * bd / bm, 0.0)
    ema, atr = np_ema(c, 200), np_atr(h, l, c, 14)
    S = dict(b=cd, s=cd, pp=0, sl=np.nan, tp=np.nan)
    EX = {}

    def orders(i, pos):
        out = []
        S["b"] += 1
        S["s"] += 1
        with np.errstate(invalid="ignore"):
            ls = z[i] < -zt and (rsi[i] < 30 if rsif else True) and (bw[i] > 0.02 if bbf else True) and (c[i] > ema[i] if emaf else True)
            ss = z[i] > zt and (rsi[i] > 70 if rsif else True) and (bw[i] > 0.02 if bbf else True) and (c[i] < ema[i] if emaf else True)
        if ls and S["b"] >= cd:
            if pos < 0:
                out.append(("close", -1))
            out.append(("entry", 1))
            S["b"], S["s"] = 0, cd
        if ss and S["s"] >= cd:
            if pos > 0:
                out.append(("close", 1))
            out.append(("entry", -1))
            S["s"], S["b"] = 0, cd
        if pos != 0 and S["pp"] == 0:
            S["sl"] = c[i] - pos * atr[i] * 2.0
            S["tp"] = c[i] + pos * atr[i] * 3.0
        if atrx and pos != 0:
            EX[i] = (pos, S["sl"], S["tp"])
        if not atrx:
            if pos > 0 and (z[i] > zx or z[i] > 0):
                out.append(("close", 1))
            if pos < 0 and (z[i] < -zx or z[i] < 0):
                out.append(("close", -1))
        S["pp"] = pos
        return out

    def lvl(i, pos, k):
        e = EX.get(i - 1)
        if e is None or e[0] != pos or np.isnan(e[1 + k]):
            return None
        return e[1 + k]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: lvl(i, pos, 0), target=lambda i, pos, ep, eb: lvl(i, pos, 1))
    ok, d = compare(run_conversion(TV_ID, df, params=params, strategy_overrides={"commission_value": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(8000, seed=404)
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({"Z-Score Threshold": 1.5, "Use RSI Confirmation": False, "Use BB Width Filter": False, "Signal Cooldown Period": 3}, (1.5, False, False, True, 3, True)),
             ({"Z-Score Threshold": 2.0, "Use ATR Stop/TP": False, "Use RSI Confirmation": False}, (2.0, False, True, True, 5, False)),
             ({"Z-Score Threshold": 1.8, "Use EMA Trend Filter": False, "Use RSI Confirmation": False, "Use BB Width Filter": False}, (1.8, False, False, False, 5, True)))
    for params, args in cases:
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
