"""Independent check — DMT Full Control Pro V2 (eKwe8KQq): hourly bars, market orders at the next open. EMA9 crosses EMA21; long needs EMA9 > EMA21, RSI14 < 70, MACD line above signal with a positive histogram, ATR14 > 1.5 % of the close (and, with the BB filter, the squeeze test
(BASIS - LOWER) / UPPER >= 0.04 where the script's 'upper' variable holds the middle band and its 'basis' the upper band); short mirrored (RSI > 30, MACD below signal with a negative histogram, EMA9 < EMA21). Modes: Long (golden entry, death close), Bidireccional (entries both ways, each cross also
closes the other side). Variants: default, both directions, both directions with the BB filter. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "eKwe8KQq"


def one(df, params, both, use_bb):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    f, s = np_ema(c, 9), np_ema(c, 21)
    gc, dc = np_cross_over(f, s), np_cross_under(f, s)
    rsi = np_rsi(c, 14)
    macd = np_ema(c, 12) - np_ema(c, 26)
    sig = np_ema(macd, 9)
    hist = macd - sig
    atr = np_atr(h, l, c, 14)
    basis = np_sma(c, 20)
    dev = 2.0 * pd.Series(c).rolling(20, min_periods=20).std(ddof=0).to_numpy()
    upper, lower = basis + dev, basis - dev
    with np.errstate(invalid="ignore", divide="ignore"):
        sq = (basis - lower) / upper < 0.04
        bb_ok = ~sq if use_bb else np.ones(n, bool)
        atr_ok = atr > c * (1.5 / 100)
        lc = gc & (f > s) & (rsi < 70) & (macd > sig) & (hist > 0) & bb_ok & atr_ok
        sc = dc & (f < s) & (rsi > 30) & (macd < sig) & (hist < 0) & bb_ok & atr_ok

    def orders(i, pos):
        out = []
        if lc[i]:
            out.append(("entry", 1))
        if sc[i] and both:
            out.append(("entry", -1))
        if dc[i]:
            out.append(("close", 1))
        if gc[i] and both:
            out.append(("close", -1))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(30000, seed=671, freq="1h")
    msgs, allok = [], True
    for params, both, bb in (({}, False, False), ({"Modo": "Bidireccional"}, True, False), ({"Modo": "Bidireccional", "Activar filtro BB (Squeeze)": True}, True, True)):
        ok, m = one(df, params, both, bb)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
