"""Independent check — NNFX BTC SSL+QQE (ymepYSLq): daily bars, process_orders_on_close, one position, reversals allowed. SSL = EMA20(close); QQE = EMA5(EMA5(RSI6)) histogram sign; Keltner = EMA20 +/- 1.5 x ATR20 on the close.
Long: close crosses over the SSL line with QQE bull and the close inside Keltner (short: crossunder, QQE bear), only inside 2020-01-01 .. 2030-12-31 UTC. While in a position the stop (1.5 ATR14) / target (3 ATR14) around the entry price
work from the next bar; at the close the opposite QQE / baseline state closes the trade (a reversal queued in the same bar closes first, so the close is then ignored). Margin and slippage off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "ymepYSLq"


def check():
    df = bars(6000, seed=273)
    t = df["time"].to_numpy()
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ssl = np_ema(c, 20)
    kcm, kca = np_ema(c, 20), np_atr(h, l, c, 20)
    up, lo = kcm + kca * 1.5, kcm - kca * 1.5
    q = np_ema(np_ema(np_rsi(c, 6), 5), 5)
    hist = np_ema(np_rsi(c, 6), 5) - q
    atr = np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        qb = hist > 0
        sb = c > ssl
        inkc = (c >= lo) & (c <= up)
        ind = (t >= 1577836800000) & (t <= 1924905600000)
        le = np_cross_over(c, ssl) & qb & inkc & ind
        se = np_cross_under(c, ssl) & ~qb & inkc & ind
    poscl = np.zeros(n)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if le[i]:
            out.append(("entry", 1))
        if se[i]:
            out.append(("entry", -1))
        if pos > 0 and (not qb[i] or not sb[i]):
            out.append(("close", 1))
        if pos < 0 and (qb[i] or sb[i]):
            out.append(("close", -1))
        return out

    def stop(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(atr[i - 1]):
            return None
        return ep - 1.5 * atr[i - 1] if pos > 0 else ep + 1.5 * atr[i - 1]

    def target(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(atr[i - 1]):
            return None
        return ep + 3.0 * atr[i - 1] if pos > 0 else ep - 3.0 * atr[i - 1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
