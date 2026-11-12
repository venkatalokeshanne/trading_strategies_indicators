"""Independent check — Confluence Rank Trend Strategy (LcA4mcE6): daily bars, one position, market orders at the next open. Directional score = trend (10 for close beyond the EMA233, 10 for EMA55 beyond it) + momentum (20 x clamp((RSI14 - 50) / 20)) + efficiency (net 20-bar move / path, full at 0.40, only in the direction of the net move) + volatility regime (ATR14 percent-rank over 200 prior bars: ramps up below 20, flat 20 between, ramps down above 85) + participation (20 x clamp(volume / SMA20(volume) - 0.5) on a bar closing in the direction). Entry when the score crosses up through the threshold (shorts mirrored, long wins a tie) while flat and past bar 233; the stop sits at close -/+ 3 ATR with the entry
and then only ratchets in the trade's favour from each close (an exit issued while in the trade works from the next bar); a score under the exit level closes at the next open. Position size does not affect the trade list (it is risk-based on equity), so only the trades are compared. Margin, slippage and commission off on the pinelib side. Variants: entry score 70, entry 55 with a 2 ATR stop, and long only with exit score 50."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_rsi, np_sma, run_conversion, simulate

TV_ID = "LcA4mcE6"


def clamp(x):
    return np.minimum(1.0, np.maximum(0.0, x))


def one(df, params, entry, exit_, smult, allow_short):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    ef, es, rsi, atr = np_ema(c, 55), np_ema(c, 233), np_rsi(c, 14), np_atr(h, l, c, 14)
    chg = c - np.r_[np.full(20, np.nan), c[:-20]]
    ad = np.abs(c - np.r_[np.nan, c[:-1]])
    path = pd.Series(ad).rolling(20).sum().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        er = np.where(path > 0, np.abs(chg) / path, 0.0)
        pr = np.full(n, 50.0)
        for i in range(201, n):
            if not np.isnan(atr[i]):
                pr[i] = 100.0 * np.sum(atr[i - 200:i] <= atr[i]) / 200
        rel = v / np_sma(v, 20)
        tl = (c > es) * 10.0 + (ef > es) * 10.0
        ts = (c < es) * 10.0 + (ef < es) * 10.0
        ml, ms = 20 * clamp((rsi - 50) / 20), 20 * clamp((50 - rsi) / 20)
        el = np.where(chg > 0, 20 * clamp(er / 0.4), 0.0)
        esc = np.where(chg < 0, 20 * clamp(er / 0.4), 0.0)
        vr = np.where(pr < 20, 20 * pr / 20, np.where(pr > 85, 20 * clamp((100 - pr) / 15), 20.0))
        pl = np.where(c > o, 20 * clamp(rel - 0.5), 0.0)
        ps = np.where(c < o, 20 * clamp(rel - 0.5), 0.0)
        sl_ = np.nan_to_num(tl + ml + el + vr + pl)
        ss_ = np.nan_to_num(ts + ms + esc + vr + ps)
    T = {}

    def orders(i, pos):
        out = []
        sd = smult * atr[i]
        warm = i > 233
        flat = pos == 0
        ls = warm and allow_long and flat and sl_[i] >= entry and sl_[i - 1] < entry
        ss = warm and allow_short and flat and ss_[i] >= entry and ss_[i - 1] < entry and not ls
        if ls:
            T[i] = c[i] - sd
            out.append(("entry", 1))
        elif ss:
            T[i] = c[i] + sd
            out.append(("entry", -1))
        elif pos > 0:
            T[i] = max(T.get(i - 1, c[i] - sd), c[i] - sd)
            if sl_[i] < exit_:
                out.append(("close", 1))
        elif pos < 0:
            T[i] = min(T.get(i - 1, c[i] + sd), c[i] + sd)
            if ss_[i] < exit_:
                out.append(("close", -1))
        return out

    allow_long = True
    stop = lambda i, pos, ep, eb: T.get(i - 1)
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop)
    ok, d = compare(run_conversion(TV_ID, df, params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "commission_value": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(6000, seed=202)
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    for params, args in (({"Entry Score": 70.0}, (70.0, 35.0, 3.0, True)),
                         ({"Entry Score": 55.0, "Trailing Stop (ATR)": 2.0}, (55.0, 35.0, 2.0, True)),
                         ({"Entry Score": 55.0, "Exit Score": 50.0, "Allow Shorts": False}, (55.0, 50.0, 3.0, False))):
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
