"""Independent check — MMF Strategy Premium / Tomukas Edge (cXpZ682G): daily bars, process_orders_on_close, one position. Long: close > EMA50 > EMA200, low <= EMA25 or EMA50, EMA3 crosses over EMA6, MACD(12,26,9) crosses over its signal,
RSI14 > 55, +DI > -DI with ADX14 > 22 and volume > SMA20 (short is the mirror, RSI < 45). Entry closes the other side first. Stop 1.2 ATR / target 1.8 ATR around the entry price are issued only while in a position at the script
run, so they work from the next bar; trail_points without trail_offset is no trailing stop. Margin and slippage off. The signal conditions are rare, so the check loosens nothing but uses a long series."""
import numpy as np

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_dmi, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "cXpZ682G"


def check():
    df = bars(30000, seed=119, freq="D")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    f, s, m, tr, mac = (np_ema(c, k) for k in (3, 6, 25, 50, 200))
    macd = np_ema(c, 12) - np_ema(c, 26)
    sig = np_ema(macd, 9)
    rsi = np_rsi(c, 14)
    atr = np_atr(h, l, c, 14)
    pdi, mdi, adx = np_dmi(h, l, c, 14)
    vok = v > np_sma(v, 20)
    with np.errstate(invalid="ignore"):
        ls = (c > tr) & (tr > mac) & ((l <= m) | (l <= tr)) & np_cross_over(f, s) & np_cross_over(macd, sig) & (rsi > 55) & (pdi > mdi) & (adx > 22) & vok
        ss = (c < tr) & (tr < mac) & ((h >= m) | (h >= tr)) & np_cross_under(f, s) & np_cross_under(macd, sig) & (rsi < 45) & (mdi > pdi) & (adx > 22) & vok
    poscl = np.zeros(n)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if ls[i]:
            out += [("close", -1), ("entry", 1)]
        if ss[i]:
            out += [("close", 1), ("entry", -1)]
        return out

    def stop(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(atr[i - 1]):
            return None
        return ep - 1.2 * atr[i - 1] if pos > 0 else ep + 1.2 * atr[i - 1]

    def target(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(atr[i - 1]):
            return None
        return ep + 1.8 * atr[i - 1] if pos > 0 else ep - 1.8 * atr[i - 1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
