"""Independent check — EMA-RSI-ATR (vpopCZIt): daily bars, long only. EMA21 > EMA89, close > EMA21, 55 < RSI14 < 75 and ATR14 > SMA20(ATR14) enter when flat. entryAtr = the ATR of the first bar on which the position is open at
the close; the exit (stop avg - 2.5 entryAtr, limit avg + 4 entryAtr) is issued from that close on, so it works from the next bar. Slippage (2 ticks in the original) and margin off on the pinelib side (see EEF1C7ly)."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "vpopCZIt"


def check():
    df = bars(6000, seed=211)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    ef, es, rsi, atr = np_ema(c, 21), np_ema(c, 89), np_rsi(c, 14), np_atr(h, l, c, 14)
    am = np_sma(atr, 20)
    with np.errstate(invalid="ignore"):
        sig = (ef > es) & (c > ef) & (rsi > 55) & (rsi < 75) & (atr > am)

    def stop(i, pos, ep, eb):
        return None if eb >= i else ep - 2.5 * atr[eb]

    def target(i, pos, ep, eb):
        return None if eb >= i else ep + 4.0 * atr[eb]

    ref = simulate(o, h, l, c, lambda i, pos: [("entry", 1)] if sig[i] and pos == 0 else [], stop=stop, target=target)
    sym = SymbolInfo.make("BINANCE:ETHUSD", "crypto", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
