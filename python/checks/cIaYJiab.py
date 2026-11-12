"""Independent check — Growth Breakout v3 (cIaYJiab): daily bars, process_orders_on_close, long only, 1 trade at a time, trade list only. Setup (inputs loosened on both sides so enough trades occur: max distance from EMA20 10%, below the 252-bar high 50%, RVOL >= 1.0):
|close - EMA20| / close <= 10%, close >= 252-bar high x 0.5, close > the highest high of the 10 bars before this one, volume / SMA20(volume) >= 1, (EMA20 crosses over EMA50 or close > EMA20), and Stochastic RSI K > D with K < 80
(raw = 100 (rsi - lowest rsi14) / (highest - lowest); 0 when the window's high equals its low or either is na; the window skips leading na but needs 14 bars; K = SMA3, D = SMA3(K), prefix-sum SMAs as in pinelib). Entry at the close.
Exit modes tested: 50 EMA Crossunder (close at the close when close crosses under EMA50) and Percent Stop + Target (2% stop / 4% target around the entry price, issued while in a position at a script run so they work from the bar after next). Margin
and slippage off, sizing 5% on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "cIaYJiab"


def psma(x, n):
    x = np.asarray(x, float)
    nanc = np.r_[0, np.cumsum(np.isnan(x))]
    P = np.r_[0.0, np.cumsum(np.where(np.isnan(x), 0.0, x))]
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        if nanc[i + 1] - nanc[i - n + 1] == 0:
            out[i] = (P[i] - P[i - (n - 1)] + x[i]) / n
    return out


def one(df, mode):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    ef, es = np_ema(c, 20), np_ema(c, 50)
    h52 = pd.Series(h).rolling(252, min_periods=252).max().to_numpy()
    prior = np.r_[np.nan, pd.Series(h).rolling(10, min_periods=10).max().to_numpy()[:-1]]
    rvol = v / np_sma(v, 20)
    rsi = np_rsi(c, 14)
    lo = pd.Series(rsi).rolling(14, min_periods=1).min().to_numpy().copy()
    hi = pd.Series(rsi).rolling(14, min_periods=1).max().to_numpy().copy()
    lo[:13] = np.nan
    hi[:13] = np.nan
    with np.errstate(invalid="ignore", divide="ignore"):
        raw = 100 * (rsi - lo) / (hi - lo)
    raw = np.where(np.isnan(hi) | np.isnan(lo) | (hi == lo), 0.0, raw)
    kk = psma(raw, 3)
    dd = psma(kk, 3)
    with np.errstate(invalid="ignore"):
        cond = ((np.abs(c - ef) / c * 100) <= 10.0) & (c >= h52 * 0.5) & (c > prior) & (rvol >= 1.0) & (np_cross_over(ef, es) | (c > ef)) & (kk > dd) & (kk < 80.0)
        ex50 = np_cross_under(c, es)
    poscl = np.zeros(n)
    ep_now = {"i": -1, "ep": np.nan}
    avg_at = np.full(n, np.nan)

    def orders(i, pos):
        poscl[i] = pos
        if pos > 0 and ep_now["i"] == i:
            avg_at[i] = ep_now["ep"]
        out = []
        if cond[i] and pos == 0:
            out.append(("entry", 1))
        if pos > 0 and mode == "50 EMA Crossunder" and ex50[i]:
            out.append(("close", 1))
        return out

    def stop(i, pos, ep, eb):
        ep_now["i"], ep_now["ep"] = i, ep
        if mode != "Percent Stop + Target" or i == 0 or poscl[i - 1] <= 0 or np.isnan(avg_at[i - 1]):
            return None
        return avg_at[i - 1] * 0.98

    def target(i, pos, ep, eb):
        if mode != "Percent Stop + Target" or i == 0 or poscl[i - 1] <= 0 or np.isnan(avg_at[i - 1]):
            return None
        return avg_at[i - 1] * 1.04

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    params = {"Exit Mode": mode, "Max Distance From Fast EMA (%)": 10.0, "Max Distance Below 52-Week High (%)": 50.0, "Minimum Relative Volume": 1.0,
              "Stop Loss (%)": 2.0, "Take Profit (%)": 4.0}
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params,
                                   strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "default_qty_value": 5}), ref)
    return ok and len(ref) > 5, f"{mode}: {d} (got {len(ref)})"


def check():
    df = bars(6000, seed=565)
    msgs, allok = [], True
    for mode in ("50 EMA Crossunder", "Percent Stop + Target"):
        ok, m = one(df, mode)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
