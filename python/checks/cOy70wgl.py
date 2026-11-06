"""Independent check — Auto-Optimized by Backpulse (cOy70wgl): daily bars, Start Year 2016 (passed to both sides; New York 2016-01-01), slippage 0. EMA14 crossing EMA44 with close beyond EMA44 (inside the window) enters long / short (next open, reversing; ignored when already on that side). The ATR trailing stop is re-seeded on every signal
(long: close - 2.5 ATR14; short: close + 2.5 ATR14), ratcheted each later bar while a position in that direction exists at script time, and cleared (na) otherwise. While a position exists (as of a bar's close) its exit is issued: stop = that trailing value, target = entry +/- 6%; it works from the next bar for the same direction."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "cOy70wgl"


def check():
    df = bars(9000, seed=320)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    f, s, atr = np_ema(c, 14), np_ema(c, 44), np_atr(h, l, c, 14)
    t0 = pd.Timestamp(year=2016, month=1, day=1, tz="America/New_York").value // 1_000_000
    inr = df["time"].to_numpy() >= t0
    with np.errstate(invalid="ignore"):
        lc = np_cross_over(f, s) & (c > s) & inr
        sc = np_cross_under(f, s) & (c < s) & inr
    st = dict(lt=np.nan, stt=np.nan)
    tmp, lv = {}, {}

    def orders(i, pos):
        out = []
        d = atr[i] * 2.5
        if lc[i]:
            st["lt"] = c[i] - d
        elif pos > 0:
            st["lt"] = max(c[i] - d if np.isnan(st["lt"]) else st["lt"], c[i] - d)
        else:
            st["lt"] = np.nan
        if sc[i]:
            st["stt"] = c[i] + d
        elif pos < 0:
            st["stt"] = min(c[i] + d if np.isnan(st["stt"]) else st["stt"], c[i] + d)
        else:
            st["stt"] = np.nan
        if lc[i]:
            out.append(("entry", 1))
        if sc[i]:
            out.append(("entry", -1))
        ep = tmp.get(i) if pos != 0 else None
        lv[i] = None if ep is None else (1 if pos > 0 else -1, ep, st["lt"] if pos > 0 else st["stt"])
        return out

    def stop(i, pos, ep, eb):
        tmp[i] = ep
        p = lv.get(i - 1) if i > 0 else None
        if p is None or p[0] * pos <= 0 or np.isnan(p[2]):
            return None
        return p[2]

    def target(i, pos, ep, eb):
        p = lv.get(i - 1) if i > 0 else None
        if p is None or p[0] * pos <= 0:
            return None
        return p[1] * 1.06 if pos > 0 else p[1] * 0.94

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Start Year": 2016},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
