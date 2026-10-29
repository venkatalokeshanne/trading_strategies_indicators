"""Independent check — RSI Volume Ladder (XuywwObg): daily bars, process_orders_on_close, pyramiding 3 (indep.simulate_pyr, on_close), 1 unit per lot (sizes do not change entries / exits).
Signal: RSI14 < 30 and volume > 1.5 x SMA20. Up to 3 lots, each needing close < last lot x (1 - 1.5%). The exit order (stop = lowest lot close x 0.97, limit = average of the lots filled before the bar's
script ran x 1.04) is issued only while long at the script, so it works from the next bar on the whole stack. On a bar where a trade closed with nothing open: classify TP/SL by the nearest of the PREVIOUS bar's levels
(ties = TP), reset the ladder, start the cooldown (3 bars after SL, 0 after TP; barsSince <= cooldown blocks the exit bar itself). Fixed 1-unit lots (so the average price is the plain mean), margin and slippage off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_rsi, np_sma, run_conversion, simulate_pyr
from pinelib import SymbolInfo

TV_ID = "XuywwObg"


def check():
    df = bars(6000, seed=451)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    rsi = np_rsi(c, 14)
    va = np_sma(v, 20)
    with np.errstate(invalid="ignore"):
        sig = (rsi < 30) & (v > va * 1.5)
    log: list = []
    S = dict(lots=[], lowest=np.nan, last=np.nan, cnt=0, tp=np.nan, sl=np.nan, leb=-9999, lsl=False)
    sl_arr = np.full(n, np.nan)
    tp_arr = np.full(n, np.nan)

    def orders(i, pos):
        prev_tp, prev_sl = S["tp"], S["sl"]
        out = []
        if log and log[-1][3] == i and pos == 0:
            real = log[-1][4]
            sl_hit = False
            if not np.isnan(prev_tp) and not np.isnan(prev_sl):
                sl_hit = abs(real - prev_tp) > abs(real - prev_sl)
            S.update(leb=i, lsl=sl_hit, tp=np.nan, sl=np.nan, lowest=np.nan, last=np.nan, cnt=0, lots=[])
        cooldown = (i - S["leb"]) <= (3 if S["lsl"] else 0)
        dropped = np.isnan(S["last"]) or c[i] < S["last"] * (1 - 0.015)
        newlot = None
        if S["cnt"] < 3 and sig[i] and dropped and not cooldown:
            out.append(("entry", 1))
            S["lowest"] = c[i] if np.isnan(S["lowest"]) else min(S["lowest"], c[i])
            S["last"] = c[i]
            S["cnt"] += 1
            newlot = c[i]
        if S["lots"]:                                   # position_size > 0 as of this script run
            S["tp"] = np.mean(S["lots"]) * 1.04
            S["sl"] = S["lowest"] * 0.97
            tp_arr[i], sl_arr[i] = S["tp"], S["sl"]
        if newlot is not None:
            S["lots"].append(newlot)
        return out

    def stop(i, d, trades):
        return None if i == 0 or np.isnan(sl_arr[i - 1]) else sl_arr[i - 1]

    def target(i, d, trades):
        return None if i == 0 or np.isnan(tp_arr[i - 1]) else tp_arr[i - 1]

    with np.errstate(invalid="ignore"):
        ref = simulate_pyr(o, h, l, c, orders, pyramiding=3, stop=stop, target=target, on_close=True, log=log)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": 1}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
