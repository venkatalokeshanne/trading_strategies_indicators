"""Independent check — ADX-SUPER TREND (DUm1QIbL): daily bars, one position, trade list only (quantities do not change entries / exits). SuperTrend(3.02, ATR5); upd/dnd = the line on the up / down side; ADX with smoothing 1 = 100 x
|DI+ - DI-| / (DI+ + DI-) from Wilder DIs of length 20 (fixnan). buyzone = upd x (1 + ADX/10000), sellzone = dnd x (1 - ADX/10000). Buy: low < buyzone and low >= lowest low of the previous 33 bars; sell: high > sellzone and high <= highest
high of the previous 17 bars; entered next open when nothing is open. While in a position at a script run the trailing stop (long: max(close x 0.98, previous stop, starting from 0 when flat), short: min(close x 1.02, previous)) and the take-profit
(entry x 1.015 / 0.985) are issued, so bar i works with bar i-1's values. Margin and slippage off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_dmi, np_supertrend, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "DUm1QIbL"


def check():
    df = bars(6000, seed=555)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    st_, dr = np_supertrend(h, l, c, 3.02, 5)
    st_ = st_.copy()
    st_[0] = np.nan
    plus, minus, _ = np_dmi(h, l, c, 20)
    sm = plus + minus
    with np.errstate(invalid="ignore", divide="ignore"):
        sig = 100.0 * np.abs(plus - minus) / np.where(sm == 0, 1.0, sm)
        upd = np.where(dr < 0, st_, np.nan)
        dnd = np.where(dr < 0, np.nan, st_)
        bz = upd * (1 + sig / 10000)
        sz = dnd * (1 - sig / 10000)
        sup = pd.Series(np.r_[np.nan, l[:-1]]).rolling(33, min_periods=33).min().to_numpy()
        res = pd.Series(np.r_[np.nan, h[:-1]]).rolling(17, min_periods=17).max().to_numpy()
        buy = (l < bz) & (l >= sup)
        sell = (h > sz) & (h <= res)
    S = dict(ls=0.0, ss=999999.0)
    poscl = np.zeros(n)
    ls_arr = np.full(n, np.nan)
    ss_arr = np.full(n, np.nan)
    ep_now = {"i": -1, "ep": np.nan}
    tp_arr = np.full(n, np.nan)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if pos > 0:
            S["ls"] = max(c[i] * 0.98, S["ls"])
        else:
            S["ls"] = 0.0
        if pos < 0:
            S["ss"] = min(c[i] * 1.02, S["ss"])
        else:
            S["ss"] = 999999.0
        ls_arr[i], ss_arr[i] = S["ls"], S["ss"]
        if pos != 0 and ep_now["i"] == i:
            tp_arr[i] = ep_now["ep"] * (1.015 if pos > 0 else 0.985)
        if pos == 0 and buy[i]:
            out.append(("entry", 1))
        if pos == 0 and sell[i]:
            out.append(("entry", -1))
        return out

    def stop(i, pos, ep, eb):
        ep_now["i"], ep_now["ep"] = i, ep
        if i == 0 or poscl[i - 1] * pos <= 0:
            return None
        return ls_arr[i - 1] if pos > 0 else ss_arr[i - 1]

    def target(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(tp_arr[i - 1]):
            return None
        return tp_arr[i - 1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
