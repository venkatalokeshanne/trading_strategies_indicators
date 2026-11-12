"""Independent check — Stock Breakout Momentum (n7sVlEUq): daily bars, one position, trade list only. Long: close > previous bar's 20-bar highest high, close > SMA50, volume > 1.2 x SMA20 (short mirrored) while flat; the
stop = signal bar OPEN -/+ 2 ATR14 and the target = open +/- 3 ATR14 are fixed at the signal; once the position exists the stop ratchets each bar to max(stop, close - 2 ATR) (min for shorts) at the script run, and the bracket
(stop, target) is re-issued so bar i works with the levels computed at bar i-1's close. The bar-20 time exit is a market close (filled at the next open) and replaces the bracket on that bar. Levels reset when flat and not
just entered. Margin and slippage off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "n7sVlEUq"


def check():
    df = bars(6000, seed=826)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    hh = pd.Series(h).rolling(20, min_periods=20).max().to_numpy()
    ll = pd.Series(l).rolling(20, min_periods=20).min().to_numpy()
    hh1, ll1 = np.r_[np.nan, hh[:-1]], np.r_[np.nan, ll[:-1]]
    atr, sma, vs = np_atr(h, l, c, 14), np_sma(c, 50), np_sma(v, 20)
    with np.errstate(invalid="ignore"):
        ready = ~np.isnan(hh1) & ~np.isnan(ll1) & ~np.isnan(atr) & ~np.isnan(sma) & ~np.isnan(vs)
        vok = v > vs * 1.2
        lb = ready & (c > hh1) & (c > sma) & vok
        sb = ready & (c < ll1) & (c < sma) & vok
    S = dict(lsl=np.nan, ssl=np.nan, ltp=np.nan, stp=np.nan, eidx=np.nan, je=False)
    poscl = np.zeros(n)
    sl_arr = np.full(n, np.nan)
    tp_arr = np.full(n, np.nan)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if lb[i] and pos == 0:
            S.update(je=True, eidx=i, lsl=o[i] - atr[i] * 2.0, ltp=o[i] + atr[i] * 3.0)
            out.append(("entry", 1))
        if sb[i] and pos == 0:
            S.update(je=True, eidx=i, ssl=o[i] + atr[i] * 2.0, stp=o[i] - atr[i] * 3.0)
            out.append(("entry", -1))
        if pos > 0:
            S["lsl"] = max(o[i] if np.isnan(S["lsl"]) else S["lsl"], c[i] - atr[i] * 2.0)
        if pos < 0:
            S["ssl"] = min(o[i] if np.isnan(S["ssl"]) else S["ssl"], c[i] + atr[i] * 2.0)
        held = not np.isnan(S["eidx"]) and (i - S["eidx"]) >= 20
        if pos != 0:
            if held:
                out.append(("close", pos))
            else:
                sl_arr[i] = S["lsl"] if pos > 0 else S["ssl"]
                tp_arr[i] = S["ltp"] if pos > 0 else S["stp"]
        if pos == 0 and not S["je"]:
            S.update(lsl=np.nan, ssl=np.nan, ltp=np.nan, stp=np.nan, eidx=np.nan)
        S["je"] = False
        return out

    def stop(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(sl_arr[i - 1]):
            return None
        return sl_arr[i - 1]

    def target(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(tp_arr[i - 1]):
            return None
        return tp_arr[i - 1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
