"""Independent check — BTC Trend-Momentum (OKxIjdsz): daily bars (all after the 2018 start gate once enough bars exist), one position (entries reverse), trade list only. CMF20 = sum20(money-flow volume) / sum20(volume);
%K = SMA3 of the stochastic of RSI14 over 14 bars (lowest / highest skip the leading na but need a full 14-bar window). Long: %K crosses over 20, CMF > 0, ATR14 > SMA20(ATR14), close > EMA200; short: %K crosses under 80, CMF < 0,
same ATR filter (no EMA condition); both after 2018-01-01 UTC. 5% sizing and margin / slippage off on the pinelib side (commission kept, it does not change the trade list)."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "OKxIjdsz"


def check():
    df = bars(6000, seed=303)
    t = df["time"].to_numpy()
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    ema = np_ema(c, 200)
    with np.errstate(invalid="ignore", divide="ignore"):
        mfm = np.where((h - l) != 0, ((c - l) - (h - c)) / (h - l), 0.0)
    cmf = pd.Series(mfm * v).rolling(20).sum().to_numpy() / pd.Series(v).rolling(20).sum().to_numpy()
    rsi = np_rsi(c, 14)
    hh = pd.Series(rsi).rolling(14, min_periods=1).max().to_numpy().copy()
    ll = pd.Series(rsi).rolling(14, min_periods=1).min().to_numpy().copy()
    hh[:13] = np.nan
    ll[:13] = np.nan
    with np.errstate(invalid="ignore", divide="ignore"):
        stoch = 100 * (rsi - ll) / (hh - ll)
    stoch[~np.isfinite(stoch)] = np.nan
    k = np_sma(stoch, 3)
    atr = np_atr(h, l, c, 14)
    volok = atr > np_sma(atr, 20)
    with np.errstate(invalid="ignore"):
        gate = t > 1514764800000
        ls = (cmf > 0) & np_cross_over(k, 20.0) & volok & gate & (c > ema)
        ss = (cmf < 0) & np_cross_under(k, 80.0) & volok & gate

    def orders(i, pos):
        out = []
        if ls[i]:
            out.append(("entry", 1))
        if ss[i]:
            out.append(("entry", -1))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "default_qty_value": 5}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
