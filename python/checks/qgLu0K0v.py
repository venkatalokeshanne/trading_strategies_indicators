"""Independent check — Decoded Volatility Expansion (qgLu0K0v): daily bars, 100 % equity. While flat a buy-stop at (highest high of the previous 20 bars + 1.5 ATR14) and a sell-stop at (lowest low of the previous 20 - 1.5 ATR14) are (re)issued at every bar close; they stay pending until filled / replaced. A stop order fills at its level when the bar's path reaches it (at the open when it gapped through). A pending order against the open position reverses it. In a long (short) the exit is re-issued every bar close with stop = middle of the zone, target = stop-entry level + 2 x |level - middle| (measured from the CURRENT bar's levels), so it works from the next bar; the fill bar itself has no exit. A na stop level (first bars) makes the entry a plain market order, as on TradingView. Uses the pending-order reference broker (simulate_ord). Margin off on the pinelib side.
Variants: defaults; 10-bar zone with a 1 ATR offset and a 1.5 risk-reward."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, run_conversion, simulate_ord

TV_ID = "qgLu0K0v"


def one(df, params, lb, am, rr):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    zh = pd.Series(np.r_[np.nan, h[:-1]]).rolling(lb, min_periods=1).max().to_numpy().copy()      # lb bars of history, na ignored
    zl = pd.Series(np.r_[np.nan, l[:-1]]).rolling(lb, min_periods=1).min().to_numpy().copy()
    zh[:lb - 1] = zl[:lb - 1] = np.nan
    atr = np_atr(h, l, c, 14)

    def orders(i, pos):
        mid = (zh[i] + zl[i]) / 2
        bs, ss = zh[i] + atr[i] * am, zl[i] - atr[i] * am
        out = []
        if pos == 0:       # a na stop level makes the order a plain market order, as on TradingView
            out += [("entry", "Long", 1, None if np.isnan(bs) else bs, None), ("entry", "Short", -1, None if np.isnan(ss) else ss, None)]
        nn = lambda v: None if np.isnan(v) else v      # a na stop / limit level is simply absent (an exit with one level left still works)
        if pos > 0:
            out.append(("exit", "L-Exit", "Long", nn(mid), nn(bs + abs(bs - mid) * rr)))
        if pos < 0:
            out.append(("exit", "S-Exit", "Short", nn(mid), nn(ss - abs(ss - mid) * rr)))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate_ord(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(4000, seed=14)
    msgs, allok = [], True
    for params, args in (({}, (20, 1.5, 2.0)), ({"Consolidation Lookback": 10, "Outlier Multiplier": 1.0, "Risk-Reward Ratio": 1.5}, (10, 1.0, 1.5))):
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
