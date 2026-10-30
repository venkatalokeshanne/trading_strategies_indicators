"""Independent check — THE GREATEST BOT EVER MADE (il2eJJNA): daily bars. Long when flat and (bullish FVG [low > high[2] with close[1] > open[1]] or MACD(12,26,9) cross over with RSI14 < 40 or [close > SMA20 and bullish FVG]) and volume > SMA20(volume) and ADX14 > 20; short mirrors
(bearish FVG, cross under with RSI > 60, close < SMA20). While a position exists (as of a bar's close) the exit applies from the next bar: stop 400 ticks (0.01) from the entry price, trailing stop activating after 100 ticks with a 50-tick offset."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_dmi, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "il2eJJNA"


def check():
    df = bars(9000, seed=5)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    rsi = np_rsi(c, 14)
    macd = np_ema(c, 12) - np_ema(c, 26)
    sig = np_ema(macd, 9)
    dp, dm, adx = np_dmi(h, l, c, 14)
    hv = v > np_sma(v, 20)
    h2, l2 = np.r_[[np.nan] * 2, h[:-2]], np.r_[[np.nan] * 2, l[:-2]]
    c1, o1 = np.r_[np.nan, c[:-1]], np.r_[np.nan, o[:-1]]
    sma20 = np_sma(c, 20)
    with np.errstate(invalid="ignore"):
        bf = (l > h2) & (c1 > o1)
        sf = (h < l2) & (c1 < o1)
        lc = (bf | (np_cross_over(macd, sig) & (rsi < 40)) | ((c > sma20) & hv & bf)) & hv & (adx > 20)
        sc = (sf | (np_cross_under(macd, sig) & (rsi > 60)) | ((c < sma20) & hv & sf)) & hv & (adx > 20)
    poscl = np.zeros(n)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if lc[i] and pos == 0:
            out.append(("entry", 1))
        if sc[i] and pos == 0:
            out.append(("entry", -1))
        return out

    def active(i, pos):
        return i > 0 and poscl[i - 1] * pos > 0

    def stop(i, pos, ep, eb):
        if not active(i, pos):
            return None
        return ep - 4.0 if pos > 0 else ep + 4.0

    def trail(i, pos, ep, eb):
        return (100, 50) if active(i, pos) else None

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, trail=trail, tick=0.01)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
