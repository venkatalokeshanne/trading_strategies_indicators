"""Independent check — EMA Ribbon + Smoothed RSI (xDJH00mL): daily bars, process_orders_on_close, one position, trade list only. Signal needs EMA10 > EMA20 (for BOTH sides); long = SMA50 of RSI21 crossing over 51
(or staying above 51 when the cross requirement is off), short = crossing under 49 (staying below 49). While flat: stop = 20-bar swing low (high) -/+ 5 ticks of 0.01, at least 20 ticks from the close, target = 2 x that distance,
fixed at the signal bar and working from the next bar. Both variants (cross required / not) run. Size 5% and margin / slippage off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "xDJH00mL"


def one(df, cross):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    rs = np_sma(np_rsi(c, 21), 50)
    tu = np_ema(c, 10) > np_ema(c, 20)
    sw_lo = pd.Series(l).rolling(20, min_periods=20).min().to_numpy()
    sw_hi = pd.Series(h).rolling(20, min_periods=20).max().to_numpy()
    with np.errstate(invalid="ignore"):
        ls = tu & (np_cross_over(rs, 51.0) if cross else rs > 51.0)
        ss = tu & (np_cross_under(rs, 49.0) if cross else rs < 49.0)
    lv = {1: None, -1: None}

    def orders(i, pos):
        out = []
        if pos == 0 and ls[i] and not np.isnan(sw_lo[i]):
            dist = max(c[i] - (sw_lo[i] - 0.05), 0.2)
            lv[1] = (c[i] - dist, c[i] + dist * 2.0)
            out.append(("entry", 1))
        if pos == 0 and ss[i] and not np.isnan(sw_hi[i]):
            dist = max((sw_hi[i] + 0.05) - c[i], 0.2)
            lv[-1] = (c[i] + dist, c[i] - dist * 2.0)
            out.append(("entry", -1))
        return out

    def stop(i, pos, ep, eb):
        return lv[pos][0] if lv[pos] else None

    def target(i, pos, ep, eb):
        return lv[pos][1] if lv[pos] else None

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    p = {"Only trigger on cross of the level (vs. staying above/below)": cross}
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params=p, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "default_qty_value": 5}), ref)
    return ok and len(ref) > 5, f"cross={cross}: {d} (got {len(ref)})"


def check():
    df = bars(6000, seed=377)
    msgs, allok = [], True
    for cr in (True, False):
        ok, m = one(df, cr)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
