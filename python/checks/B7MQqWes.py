"""Independent check — EWO,RSI Exhaustion Filter (B7MQqWes): daily bars, one position (entries reverse), 1 unit. EWO = SMA5(hl2) - SMA34(hl2); MFI14 of hlc3 (flows = volume x price on up / down changes); RSI14; volume > 0.8 x SMA20(volume).
oversold_zone arms when RSI < 30 and is cleared after a raw buy is evaluated (the buy test uses the zone before clearing). raw_buy = RSI crosses over 40, MFI > 30, EWO rising, volume ok, and (close above the previous 10 bars' highest
high or the zone); raw_sell = RSI crosses under 60, MFI < 70, EWO falling, volume ok. A raw signal fires only if it differs from the last fired one. Margin and slippage off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "B7MQqWes"


def np_mfi(src, vol, n):
    ch = np.r_[np.nan, np.diff(src)]
    up = np.where(ch <= 0, 0.0, src) * vol
    dn = np.where(ch >= 0, 0.0, src) * vol
    up[0] = dn[0] = np.nan
    su = pd.Series(up).rolling(n).sum().to_numpy()
    sd = pd.Series(dn).rolling(n).sum().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        return 100.0 - 100.0 / (1.0 + su / sd)


def check():
    df = bars(5000, seed=282)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    hl2, hlc3 = (h + l) / 2, (h + l + c) / 3
    ewo = np_sma(hl2, 5) - np_sma(hl2, 34)
    ewo1 = np.r_[np.nan, ewo[:-1]]
    rsi = np_rsi(c, 14)
    mfi = np_mfi(hlc3, v, 14)
    vok = v > np_sma(v, 20) * 0.8
    hh1 = np.r_[np.nan, pd.Series(h).rolling(10, min_periods=10).max().to_numpy()[:-1]]
    cu, cd = np_cross_over(rsi, 40.0), np_cross_under(rsi, 60.0)
    S = dict(zone=False, last=0)

    def orders(i, pos):
        out = []
        with np.errstate(invalid="ignore"):
            if rsi[i] < 30:
                S["zone"] = True
            brk = c[i] > hh1[i]
            rb = bool(cu[i] and mfi[i] > 30 and ewo[i] > ewo1[i] and vok[i] and (brk or S["zone"]))
            rs = bool(cd[i] and mfi[i] < 70 and ewo[i] < ewo1[i] and vok[i])
        if rb:
            S["zone"] = False
        if rb and S["last"] != 1:
            S["last"] = 1
            out.append(("entry", 1))
        if rs and S["last"] != -1:
            S["last"] = -1
            out.append(("entry", -1))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
