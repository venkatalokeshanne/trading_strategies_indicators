"""Independent check — Kinetic Kalman Breakout (nd8EpyQ5): daily bars. Plain-Python scalar Kalman filter (state [price, velocity], 2x2 covariance written out as in the textbook predict / update with F = [[1,1],[0,1]],
H = [1,0], Q = diag(0.05, 0.0001), R = 250); bands = filter +/- 2.6 * SMA200 of |close - filter|. A close crossing over the upper band goes long, under the lower band short (reversing, pyramiding 1)."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "nd8EpyQ5"


def check():
    df = bars(6000, seed=221)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    x = np.array([c[0], 0.0])
    P = np.eye(2)
    F = np.array([[1.0, 1.0], [0.0, 1.0]])
    Q = np.diag([0.05, 0.0001])
    R = 250.0
    kal = np.empty(n)
    for i in range(n):
        xp = F @ x
        Pp = F @ P @ F.T + Q
        y = c[i] - xp[0]
        S = Pp[0, 0] + R
        K = np.array([Pp[0, 0], Pp[1, 0]]) / S
        x = xp + K * y
        P = (np.eye(2) - np.outer(K, [1.0, 0.0])) @ Pp
        kal[i] = x[0]
    mae = np_sma(np.abs(c - kal), 200)
    up, lo = kal + 2.6 * mae, kal - 2.6 * mae
    bull, bear = np_cross_over(c, up), np_cross_under(c, lo)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if bull[i] else []) + ([("entry", -1)] if bear[i] else []))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
