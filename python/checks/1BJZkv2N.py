"""Independent check — Alpha TRIX Strategy (1BJZkv2N): daily bars, one position (reversals allowed), trade list only. Choppiness = 100 x log10(sum14(TR) / (highest high14 - lowest low14)) / log10(14) < 50 and ADX7 (DMI 7/7) > 20,
EMA200 trend side, TRIX = ROC(EMA8(EMA8(EMA8(close))), 1) crossing zero (|slope| >= 0 always true). Enter at the next open when flat, or reverse on an opposite signal. The ATR7 target (1.5x) and stop (1.0x) distances are locked at the signal bar
(also when the bar only reverses) and placed around the position average price while in a position at a script run: bar i works with bar i-1's locked values and entry price, only if a position of the same side existed at
bar i-1's script run. Margin and slippage off on the pinelib side (default sizing kept; the trade list is size independent)."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_dmi, np_ema, np_tr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "1BJZkv2N"


def check():
    df = bars(6000, seed=494)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    rng = pd.Series(h).rolling(14).max().to_numpy() - pd.Series(l).rolling(14).min().to_numpy()
    tr_sum = pd.Series(np_tr(h, l, c, True)).rolling(14).sum().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        chop = np.where(rng == 0, 0.0, 100 * np.log10(tr_sum / rng) / np.log10(14))
    _, _, adx = np_dmi(h, l, c, 7)
    ema = np_ema(c, 200)
    e3 = np_ema(np_ema(np_ema(c, 8), 8), 8)
    trix = 100.0 * (e3 / np.r_[np.nan, e3[:-1]] - 1.0)
    atr = np_atr(h, l, c, 7)
    with np.errstate(invalid="ignore"):
        fm = (chop < 50.0) & (adx > 20.0)
        el = fm & (c > ema) & np_cross_over(trix, 0.0)
        es = fm & (c < ema) & np_cross_under(trix, 0.0)
    S = dict(tp=np.nan, sl=np.nan)
    poscl = np.zeros(n)
    tp_arr = np.full(n, np.nan)
    sl_arr = np.full(n, np.nan)
    ep_now = {"i": -1, "ep": np.nan}
    avg_at = np.full(n, np.nan)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if pos != 0 and ep_now["i"] == i:
            avg_at[i] = ep_now["ep"]
        if el[i] and (pos == 0 or pos < 0):
            S["tp"], S["sl"] = atr[i] * 1.5, atr[i] * 1.0
            out.append(("entry", 1))
        if es[i] and (pos == 0 or pos > 0):
            S["tp"], S["sl"] = atr[i] * 1.5, atr[i] * 1.0
            out.append(("entry", -1))
        tp_arr[i], sl_arr[i] = S["tp"], S["sl"]
        return out

    def stop(i, pos, ep, eb):
        ep_now["i"], ep_now["ep"] = i, ep
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(avg_at[i - 1]):
            return None
        return avg_at[i - 1] - pos * sl_arr[i - 1]

    def target(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(avg_at[i - 1]):
            return None
        return avg_at[i - 1] + pos * tp_arr[i - 1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
