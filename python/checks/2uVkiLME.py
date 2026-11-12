"""Independent check — KAMA Strategy (2uVkiLME): daily bars, one position, trade list only. The script's own KAMA recursion: ER = |c - c[10]| / sum(|c - c[1]|, 10), SC = (ER x (2/6 - 2/51) + 2/51)^2, seeded with the
source on bar 0, na from bar 1 while SC is na, re-seeded with the source on the first bar after SC exists, then prev + SC x (close - prev). Long when KAMA is above its previous 10 values, close > SMA200 and RSI14 > 50
(short: below, <, <); the opposite side is closed first (ignored when not open) and an entry is placed only with nothing open at the script run (so a reversal needs a second bar). The stop is fixed at the signal close -/+ 2.5 ATR14,
issued with the entry. Variants: Long only and Long and Short. Margin and slippage off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_atr, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "2uVkiLME"


def kama_series(c):
    n = len(c)
    k = np.full(n, np.nan)
    fast, slow = 2 / 6, 2 / 51
    for i in range(n):
        prev = k[i - 1] if i > 0 else np.nan
        if i >= 10:
            sc = ((abs(c[i] - c[i - 10]) / sum(abs(c[j] - c[j - 1]) for j in range(i - 9, i + 1))) * (fast - slow) + slow) ** 2
        else:
            sc = np.nan
        k[i] = c[i] if np.isnan(prev) else prev + sc * (c[i] - (0 if np.isnan(prev) else prev))
    return k


def one(df, mode):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    k = kama_series(c)
    rising = np.zeros(n, bool)
    falling = np.zeros(n, bool)
    for i in range(10, n):
        w = k[i - 10:i]
        with np.errstate(invalid="ignore"):
            rising[i] = bool(np.all(k[i] > w))
            falling[i] = bool(np.all(k[i] < w))
    sma, rsi, atr = np_sma(c, 200), np_rsi(c, 14), np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        lc = rising & (c > sma) & (rsi > 50)
        sc_ = falling & (c < sma) & (rsi < 50)
    lv = {1: None, -1: None}

    def orders(i, pos):
        out = []
        if lc[i]:
            if pos < 0:
                out.append(("close", -1))
            if mode != "Short" and pos == 0:
                out.append(("entry", 1))
                lv[1] = c[i] - atr[i] * 2.5
        elif sc_[i]:
            if pos > 0:
                out.append(("close", 1))
            if mode != "Long" and pos == 0:
                out.append(("entry", -1))
                lv[-1] = c[i] + atr[i] * 2.5
        return out

    def stop(i, pos, ep, eb):
        return lv[pos]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Order Direction": mode}, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 5, f"{mode}: {d} (got {len(ref)})"


def check():
    df = bars(6000, seed=466)
    msgs, allok = [], True
    for mode in ("Long", "Long and Short"):
        ok, m = one(df, mode)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
