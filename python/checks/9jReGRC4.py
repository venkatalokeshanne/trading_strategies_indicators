"""Independent check — OmniTrend ATR Scalper (9jReGRC4): hourly bars, "Both". Stepping trend line: starts at close[0]; with ATR200 available, d = close - line; a reversal when the direction is down and d > 2 ATR (long signal) or up and -d > 2 ATR
(short); step = ATR/5 when |d| > 1 ATR else ATR/10, refreshed on a signal, on a change of that regime flag or while the step is 0; line += dir * step. Signal bars store stop = close -/+ 2 ATR, target = close +/- 3 ATR and enter that way
(reversing). One exit without from_entry is re-issued every bar from those vars: bar i uses the values as of bar i-1. Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_atr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "9jReGRC4"


def check():
    df = bars(20000, seed=311, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr = np_atr(h, l, c, 200)
    line, tdir, step, fast = c[0], 1, 0.0, False
    sl = tp = np.nan
    sig_l, sig_s = np.zeros(n, bool), np.zeros(n, bool)
    sls, tps = np.full(n, np.nan), np.full(n, np.nan)
    for i in range(n):
        if not np.isnan(atr[i]):
            d = c[i] - line
            sl_i = tdir == -1 and d > 2.0 * atr[i]
            ss_i = tdir == 1 and -d > 2.0 * atr[i]
            if sl_i:
                tdir = 1
            elif ss_i:
                tdir = -1
            chk = abs(d) > 1.0 * atr[i]
            if sl_i or ss_i or (chk != fast) or step == 0.0:
                fast = chk
                step = atr[i] / 5 if fast else atr[i] / 10
            line = line + tdir * step
            sig_l[i], sig_s[i] = sl_i, ss_i
            if sl_i:
                sl, tp = c[i] - atr[i] * 2.0, c[i] + atr[i] * 3.0
            if ss_i:
                sl, tp = c[i] + atr[i] * 2.0, c[i] - atr[i] * 3.0
        sls[i], tps[i] = sl, tp
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if sig_l[i] else []) + ([("entry", -1)] if sig_s[i] else []),
                   stop=lambda i, pos, ep, eb: None if (i == 0 or np.isnan(sls[i - 1])) else sls[i - 1],
                   target=lambda i, pos, ep, eb: None if (i == 0 or np.isnan(tps[i - 1])) else tps[i - 1])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
