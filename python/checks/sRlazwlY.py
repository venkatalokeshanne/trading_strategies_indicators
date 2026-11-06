"""Independent check — Rudy Range Regime v2 (sRlazwlY; kJ3E1iWN is the same script): daily bars, long only (1 unit). Flat regime = ADX14 < 25, 35 < RSI14 < 65, (upper - lower) / basis * 100 < 8 on Bollinger(20, 2); buys when flat. holdCount counts bars
with a position open at the close (the script's pre-fill view), reset on entry; at the close it reaches 21, or when 100 * (close - signal close) / signal close < -5, the position closes at the next open. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_adx, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "sRlazwlY"
SEED = 278


def build(tv_id, seed):
    df = bars(12000, seed=seed)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    adx, rsi = np_adx(h, l, c, 14), np_rsi(c, 14)
    mid = np_sma(c, 20)
    sd = pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        width = (4 * sd) / mid * 100
        flat = (adx < 25) & (rsi > 35) & (rsi < 65) & (width < 8.0)
    st = dict(hold=0, basis=0.0)

    def orders(i, pos):
        out = []
        if flat[i] and pos == 0:
            out.append(("entry", 1)); st["hold"] = 0; st["basis"] = c[i]
        if pos > 0:
            st["hold"] += 1
            dd = (c[i] - st["basis"]) / st["basis"] * 100
            closed = False
            if st["hold"] >= 21:
                out.append(("close", 1)); st["hold"] = 0; closed = True
            if dd < -5.0:
                if not closed:
                    out.append(("close", 1))
                st["hold"] = 0
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(tv_id, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"


def check():
    return build(TV_ID, SEED)
