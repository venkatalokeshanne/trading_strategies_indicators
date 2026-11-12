"""Independent check — BB + RSI 1:2 (3e6VE1ZG; hSG5Az26 is the same script): 4-hour bars. Close < lower Bollinger(20, 2 pop-stdev) with RSI14 < 30 buys, close > upper with RSI > 70 sells short, when flat. Entry + exit on the signal bar (stop
0.5 %, target 1 %, both from the signal close), so the bracket works from the fill bar. Margin off on the pinelib side (the risk-sized quantity exceeds equity)."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "3e6VE1ZG"
SEED = 300


def build(tv_id, seed):
    df = bars(30000, seed=seed, freq="4h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    mid = np_sma(c, 20)
    sd = pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    up, lo = mid + 2 * sd, mid - 2 * sd
    rsi = np_rsi(c, 14)
    with np.errstate(invalid="ignore"):
        ls, ss = (c < lo) & (rsi < 30), (c > up) & (rsi > 70)
    lvl = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}

    def orders(i, pos):
        out = []
        if ls[i] and pos == 0:
            out.append(("entry", 1)); lvl[1] = (c[i] * 0.995, c[i] * 1.01)
        if ss[i] and pos == 0:
            out.append(("entry", -1)); lvl[-1] = (c[i] * 1.005, c[i] * 0.99)
        return out

    ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: lvl[pos][0], target=lambda i, pos, ep, eb: lvl[pos][1])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(tv_id, df, symbol=sym, tf="240", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"


def check():
    return build(TV_ID, SEED)
