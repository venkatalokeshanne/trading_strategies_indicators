"""Independent check — Percent Supertrend, long only (sPNx5Z74): hourly bars with a 0.5 % distance (the 20 % default never flips on these bars; passed to both
sides). finalUpper/finalLower ratchet around hl2 +/- distance, trend flips when the close crosses the PREVIOUS bar's opposite band; long when the trend turns up,
closed when it turns down. Plain loop with the script's na handling."""
import numpy as np

from indep import bars, compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "sPNx5Z74"
PERC = 0.5


def check():
    df = bars(12000, seed=158, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    p = PERC / 100
    fu, fl = np.full(n, np.nan), np.full(n, np.nan)
    tr = np.zeros(n)
    prev_tr = np.nan
    entry, exit_ = np.zeros(n, bool), np.zeros(n, bool)
    for i in range(n):
        s = (h[i] + l[i]) / 2
        ub, lb = s * (1 + p), s * (1 - p)
        pfu = fu[i - 1] if i else np.nan
        pfl = fl[i - 1] if i else np.nan
        fu[i] = ub if np.isnan(pfu) else (ub if c[i - 1] > pfu else min(ub, pfu))
        fl[i] = lb if np.isnan(pfl) else (lb if c[i - 1] < pfl else max(lb, pfl))
        t = 1 if np.isnan(prev_tr) else prev_tr
        if i and c[i] > pfu:
            t = 1
        elif i and c[i] < pfl:
            t = -1
        tr[i] = t
        entry[i] = t == 1 and prev_tr == -1
        exit_[i] = t == -1 and prev_tr == 1
        prev_tr = t
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if entry[i] else []) + ([("close", 1)] if exit_[i] and pos > 0 else []))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", params={"Prozent Abstand": PERC}, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
