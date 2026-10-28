"""Independent check — NQ SCALP FIX (1B4vXkpF): daily bars, long and short. EMA5/24/150 stacked, close crossing EMA5 with RSI14 > 55 / < 45 enters when flat. While a position exists (as of a bar's close) the stop (1.5 ATR14) and target
(2.5 ATR14) around the position average price are issued, so bar i works with bar i-1's ATR and only if a position existed at bar i-1's close."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "1B4vXkpF"


def check():
    df = bars(8000, seed=41)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    f, m, s = np_ema(c, 5), np_ema(c, 24), np_ema(c, 150)
    rsi, atr = np_rsi(c, 14), np_atr(h, l, c, 14)
    # v6 `and` short-circuits: crossover/crossunder only run (and only advance their history) on bars where the EMA stack holds
    lg, sh = np.zeros(n, bool), np.zeros(n, bool)
    pu = pl = None
    with np.errstate(invalid="ignore"):
        for i in range(n):
            if f[i] > m[i] and m[i] > s[i]:
                lg[i] = pu is not None and c[i] > f[i] and pu[0] <= pu[1] and rsi[i] > 55
                pu = (c[i], f[i])
            if f[i] < m[i] and m[i] < s[i]:
                sh[i] = pl is not None and c[i] < f[i] and pl[0] >= pl[1] and rsi[i] < 45
                pl = (c[i], f[i])
    poscl = np.zeros(n)

    def orders(i, pos):
        poscl[i] = pos
        if pos != 0:
            return []
        return [("entry", 1)] if lg[i] else [("entry", -1)] if sh[i] else []

    def stop(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] == 0:
            return None
        return ep - atr[i - 1] * 1.5 if pos > 0 else ep + atr[i - 1] * 1.5

    def target(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] == 0:
            return None
        return ep + atr[i - 1] * 2.5 if pos > 0 else ep - atr[i - 1] * 2.5

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
