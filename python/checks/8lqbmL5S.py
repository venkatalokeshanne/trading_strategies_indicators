"""Independent check — BB Short DCA (8lqbmL5S): 14-hour bars, 1 unit per lot (indep.simulate_pyr, pyramiding 3; lot sizes only matter for the script's own average price, which is rebuilt here with the USD weights).
Window from 2026-01-01 New York time, signal close > upper BB(20, 2) x (1 + 0%) (threshold input set to 0 on both sides so signals occur). The three stage blocks run in sequence on one bar: lot 1 on a signal when flat, then
the stage-1 test (low <= 97% of lot 1 -> close_all; high >= 102% of lot 1 -> lot 2) on the SAME bar, then stage 2 (weighted average, 104% of lot 2 -> lot 3), then stage 3. close_all is ignored when nothing is open
at that bar's close. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_sma, run_conversion, simulate_pyr
from pinelib import SymbolInfo

TV_ID = "8lqbmL5S"


def check():
    df = bars(8500, seed=902, freq="14h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    start = int(pd.Timestamp("2026-01-01", tz="America/New_York").value // 1_000_000)
    win = df["time"].to_numpy() >= start
    basis = np_sma(c, 20)
    upper = basis + 2.0 * pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    with np.errstate(invalid="ignore"):
        sig = c > upper
    U1, U2, U3, TP = 3000.0, 6000.0, 12000.0, 0.03
    st = {"p": [None, None, None]}

    def orders(i, pos):
        out = []
        p = st["p"]
        if pos == 0:
            p[:] = [None, None, None]
        if sig[i] and pos == 0 and win[i]:
            out.append(("entry", -1))
            p[0] = c[i]
        if p[0] is not None and p[1] is None:
            if l[i] <= p[0] * (1 - TP) and pos != 0:
                out.append(("close_all",))
            if h[i] >= p[0] * 1.02:
                out.append(("entry", -1))
                p[1] = c[i]
        if p[0] is not None and p[1] is not None and p[2] is None:
            avg = (p[0] * U1 + p[1] * U2) / (U1 + U2)
            if l[i] <= avg * (1 - TP) and pos != 0:
                out.append(("close_all",))
            if h[i] >= p[1] * 1.04:
                out.append(("entry", -1))
                p[2] = c[i]
        if p[0] is not None and p[1] is not None and p[2] is not None:
            avg = (p[0] * U1 + p[1] * U2 + p[2] * U3) / (U1 + U2 + U3)
            if l[i] <= avg * (1 - TP) and pos != 0:
                out.append(("close_all",))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate_pyr(o, h, l, c, orders, pyramiding=3)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="840", params={"Ile % ponad BB": 0.0},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
