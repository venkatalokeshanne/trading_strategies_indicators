"""Independent check — Trend + RSI Enhanced (wigMmPHd): 5-min bars, process_orders_on_close (fills at the signal close). Trend (EMA 9/21) plus
RSI vs 50 enters when flat; unconditional exits with bar i-1's close -/+ 1.5 ATR stop and +/- 3 ATR target, working from the bar after the
fill. Slippage (2 ticks in the original) is set to 0 on the pinelib side: indep.simulate models slippage on market fills only."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "wigMmPHd"


def check():
    df = bars(20000, seed=111, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    f, s, rsi, atr = np_ema(c, 9), np_ema(c, 21), np_rsi(c, 14), np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        lg, sg = (f > s) & (rsi > 50), (f < s) & (rsi < 50)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if lg[i] and pos == 0 else []) + ([("entry", -1)] if sg[i] and pos == 0 else []),
                   stop=lambda i, pos, ep, eb: (c[i - 1] - 1.5 * atr[i - 1] if pos > 0 else c[i - 1] + 1.5 * atr[i - 1]) if i > eb else None,
                   target=lambda i, pos, ep, eb: (c[i - 1] + 3.0 * atr[i - 1] if pos > 0 else c[i - 1] - 3.0 * atr[i - 1]) if i > eb else None,
                   on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
