"""Independent check — EMA-RSI-ATR 4H (193w3Pua): 4-hour crypto bars, long only. EMA21 > EMA89, close > EMA21, 55 <= RSI14 <= 75 and ATR14 > SMA20(ATR14) enter when flat. The stop (close - 2.5 ATR) and limit (close + 4 ATR)
of the SIGNAL bar are kept in vars; the exit is issued only while a position is open at the close, so it works from the bar after the fill. Slippage (2 ticks) and margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "193w3Pua"


def check():
    df = bars(30000, seed=217, freq="4h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    ef, es, rsi, atr = np_ema(c, 21), np_ema(c, 89), np_rsi(c, 14), np_atr(h, l, c, 14)
    am = np_sma(atr, 20)
    with np.errstate(invalid="ignore"):
        sig = (ef > es) & (c > ef) & (rsi >= 55) & (rsi <= 75) & (atr > am)
    sl = [np.nan]
    tp = [np.nan]

    def orders(i, pos):
        if sig[i] and pos == 0:
            sl[0], tp[0] = c[i] - atr[i] * 2.5, c[i] + atr[i] * 4.0
            return [("entry", 1)]
        return []

    ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: None if eb >= i else sl[0],
                   target=lambda i, pos, ep, eb: None if eb >= i else tp[0])
    sym = SymbolInfo.make("BINANCE:ETHUSD", "crypto", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="240", strategy_overrides={"slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
