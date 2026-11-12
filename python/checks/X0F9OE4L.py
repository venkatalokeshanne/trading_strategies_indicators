"""Independent check — EMA Ribbon Fan Angle (X0F9OE4L): daily bars, one position, trade list only. Slope of EMA k = (EMA - EMA[5]) / EMA[5] x 100 for k in 8, 13, 21, 34, 55; fan up = all slopes > 0 and s8 > s13 > s21 > s34 > s55 (mirror
for down); fan score = s8 - s55. Long when fan up, score > 0.8, 50 < RSI14 < 70 and volume > SMA20(volume), flat (short: fan down, score < -0.8, 30 < RSI < 50). Stop = close -/+ 2 ATR14 and target 2R, fixed at the signal bar and working from
the fill bar; a fan that stopped widening (not increasing) or score < 0.2 (> -0.2) closes an open trade at the next open. Margin and slippage off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "X0F9OE4L"


def check():
    df = bars(7000, seed=702)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    sl = []
    for k in (8, 13, 21, 34, 55):
        e = np_ema(c, k)
        sl.append((e - np.r_[np.full(5, np.nan), e[:-5]]) / np.r_[np.full(5, np.nan), e[:-5]] * 100)
    s8, s13, s21, s34, s55 = sl
    rsi = np_rsi(c, 14)
    vok = v > np_sma(v, 20)
    atr = np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        inc_up = (s8 > s13) & (s13 > s21) & (s21 > s34) & (s34 > s55)
        inc_dn = (s8 < s13) & (s13 < s21) & (s21 < s34) & (s34 < s55)
        up = (s8 > 0) & (s13 > 0) & (s21 > 0) & (s34 > 0) & (s55 > 0) & inc_up
        dn = (s8 < 0) & (s13 < 0) & (s21 < 0) & (s34 < 0) & (s55 < 0) & inc_dn
        score = s8 - s55
        el = up & (score > 0.8) & (rsi > 50) & (rsi < 70) & vok
        es = dn & (score < -0.8) & (rsi < 50) & (rsi > 30) & vok
        xl = ~inc_up | (score < 0.2)
        xs = ~inc_dn | (score > -0.2)
    lv = {1: None, -1: None}

    def orders(i, pos):
        out = []
        if pos == 0 and el[i]:
            d = atr[i] * 2.0
            lv[1] = (c[i] - d, c[i] + d * 2.0)
            out.append(("entry", 1))
        if pos == 0 and es[i]:
            d = atr[i] * 2.0
            lv[-1] = (c[i] + d, c[i] - d * 2.0)
            out.append(("entry", -1))
        if pos > 0 and xl[i]:
            out.append(("close", 1))
        if pos < 0 and xs[i]:
            out.append(("close", -1))
        return out

    def stop(i, pos, ep, eb):
        return lv[pos][0] if lv[pos] else None

    def target(i, pos, ep, eb):
        return lv[pos][1] if lv[pos] else None

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
