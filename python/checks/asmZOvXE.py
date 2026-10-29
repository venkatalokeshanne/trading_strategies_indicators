"""Independent check — EMA + Fibonacci Pivot Break (asmZOvXE): 15-minute bars (24h synthetic), process_orders_on_close, one position, trade list only. Pivot period = the trading day (09:30-NY 1440-minute blocks); P = (H + L + C) / 3 of the PREVIOUS
period, seen by every bar of the current one (lookahead on); Fibonacci R1 = P + 0.382 x range, S1 = P - 0.382 x range. Long: green candle that opens <= EMA9 and <= R1 and closes above both; short: red candle opening >= EMA9 and >= S1
and closing below both; flat. Stop = signal candle low (high), target = close +/- 2 x risk, placed with the entry at the close and working from the next bar. Margin and slippage off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_ema, np_periods, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "asmZOvXE"


def check():
    df = bars(12000, seed=667, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    pid, _ = np_periods(df, 1440)
    npd = pid[-1] + 1
    ph = np.array([h[pid == k].max() for k in range(npd)])
    pl = np.array([l[pid == k].min() for k in range(npd)])
    pc = np.array([c[pid == k][-1] for k in range(npd)])
    r1 = np.full(n, np.nan)
    s1 = np.full(n, np.nan)
    for i in range(n):
        k = pid[i] - 1
        if k >= 0:
            p = (ph[k] + pl[k] + pc[k]) / 3.0
            rg = ph[k] - pl[k]
            r1[i], s1[i] = p + rg * 0.382, p - rg * 0.382
    ema = np_ema(c, 9)
    with np.errstate(invalid="ignore"):
        lb = (c > o) & (o <= ema) & (o <= r1) & (c > ema) & (c > r1)
        sb = (c < o) & (o >= ema) & (o >= s1) & (c < ema) & (c < s1)
    lv = {1: None, -1: None}

    def orders(i, pos):
        out = []
        if pos == 0 and lb[i] and (c[i] - l[i]) > 0:
            lv[1] = (l[i], c[i] + (c[i] - l[i]) * 2.0)
            out.append(("entry", 1))
        if pos == 0 and sb[i] and (h[i] - c[i]) > 0:
            lv[-1] = (h[i], c[i] - (h[i] - c[i]) * 2.0)
            out.append(("entry", -1))
        return out

    def stop(i, pos, ep, eb):
        return lv[pos][0] if lv[pos] else None

    def target(i, pos, ep, eb):
        return lv[pos][1] if lv[pos] else None

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
