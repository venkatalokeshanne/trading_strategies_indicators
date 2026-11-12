"""Independent check — Lobster Channel Breakout (6MgStabF): daily bars, one position (entries reverse), trade list only. Channel = highest / lowest close of the previous 20 bars; signal = first bar closing beyond it (not also beyond the
previous bar's channel). The signal bar issues entry + exit (stop close -/+ 1.5 ATR14, limit close +/- 3 ATR14; a signal while already in a position re-issues the exit with the new levels). Once a position at a script run is >= 1% in profit
the trail is activated for the rest of the trade: long trail = max(old trail (starts at the signal stop), close - 2 ATR) and the exit is re-issued with it; the short side starts its trail at the TAKE-PROFIT level (as written in the original) and uses
min(old, close + 2 ATR), so its stop sits below the market. The working order is the last one issued, evaluated from the next bar. Margin and slippage off, 5% size on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "6MgStabF"


def check():
    df = bars(6000, seed=206)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr = np_atr(h, l, c, 14)
    hi = pd.Series(c).rolling(20, min_periods=20).max().to_numpy()
    lo = pd.Series(c).rolling(20, min_periods=20).min().to_numpy()
    up, dn = np.r_[np.nan, hi[:-1]], np.r_[np.nan, lo[:-1]]
    up1, dn1 = np.r_[np.nan, up[:-1]], np.r_[np.nan, dn[:-1]]
    c1 = np.r_[np.nan, c[:-1]]
    with np.errstate(invalid="ignore"):
        ls = (c > up) & ~(c1 > up1)
        ss = (c < dn) & ~(c1 < dn1)
    S = dict(sl=np.nan, tp=np.nan, trail=np.nan, on=False, atp=np.nan)
    order = {1: None, -1: None}
    poscl = np.zeros(n)
    ep_now = {"i": -1, "ep": np.nan}

    def orders(i, pos):
        poscl[i] = pos
        out = []
        avg = ep_now["ep"] if (pos != 0 and ep_now["i"] == i) else np.nan
        if pos > 0:
            if (c[i] - avg) / avg * 100 >= 1.0:
                S["on"] = True
            if S["on"]:
                nt = c[i] - atr[i] * 2.0
                S["trail"] = max(0.0 if np.isnan(S["trail"]) else S["trail"], nt)
                S["sl"] = S["trail"]
        if pos < 0:
            if (avg - c[i]) / avg * 100 >= 1.0:
                S["on"] = True
            if S["on"]:
                nt = c[i] + atr[i] * 2.0
                S["trail"] = min(999999.0 if np.isnan(S["trail"]) else S["trail"], nt)
                S["sl"] = S["trail"]
        if ls[i]:
            S["sl"], S["tp"] = c[i] - atr[i] * 1.5, c[i] + atr[i] * 3.0
            S["atp"], S["trail"], S["on"] = S["tp"], S["sl"], False
            order[1] = (S["sl"], S["atp"])
            out.append(("entry", 1))
        if ss[i]:
            S["sl"], S["tp"] = c[i] + atr[i] * 1.5, c[i] - atr[i] * 3.0
            S["atp"], S["trail"], S["on"] = S["tp"], S["tp"], False
            order[-1] = (S["sl"], S["atp"])
            out.append(("entry", -1))
        if pos > 0 and S["on"]:
            order[1] = (S["sl"], S["atp"])
        if pos < 0 and S["on"]:
            order[-1] = (S["sl"], S["atp"])
        return out

    def stop(i, pos, ep, eb):
        ep_now["i"], ep_now["ep"] = i, ep
        return order[pos][0] if order[pos] else None

    def target(i, pos, ep, eb):
        return order[pos][1] if order[pos] else None

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "default_qty_value": 5}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
