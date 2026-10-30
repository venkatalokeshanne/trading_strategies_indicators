"""Independent check — EMA-RSLAIK Diario (Igq6XlXA): 5-min bars, long only. EMA21>EMA89 with the close above EMA21, RSI 55-75 and ATR
above its SMA20. While a trade is open the exit is re-issued every bar with levels from the entry price and the CURRENT ATR
(-2.5 / +4), so bar i works with bar i-1's levels once the trade exists (i > fill bar). Slippage is set to 0 on both sides
(strategy_overrides) because indep.simulate models slippage on market fills only; commission never changes prices."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "Igq6XlXA"


def check():
    df = bars(20000, seed=90, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    e21, e89, rsi, atr = np_ema(c, 21), np_ema(c, 89), np_rsi(c, 14), np_atr(h, l, c, 14)
    atr_ma = np_sma(atr, 20)
    with np.errstate(invalid="ignore"):
        sig = (e21 > e89) & (c > e21) & (rsi >= 55) & (rsi <= 75) & (atr > atr_ma)
    ref = simulate(o, h, l, c, lambda i, pos: [("entry", 1)] if sig[i] else [],
                   stop=lambda i, pos, ep, eb: ep - atr[i - 1] * 2.5 if i > eb else None,
                   target=lambda i, pos, ep, eb: ep + atr[i - 1] * 4 if i > eb else None)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
