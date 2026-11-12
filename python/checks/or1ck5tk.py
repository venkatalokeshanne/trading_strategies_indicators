"""Independent check — TSLA Combo D (or1ck5tk; or1ck5tk is the same logic): daily bars, margin off. n1 = EMA10(hlc3), n2 = EMA10(|hlc3 - n1|), ci = (hlc3 - n1)/(0.015 n2), tci = EMA21(ci); comb = (RSI14 + raw stoch14(close, high, low))/2; blueWave = EMA6(comb) - EMA35(comb) + tci/2;
money flow = EMA5(MFI60(hlc3) - 50) * 0.8 with MFI = 100 - 100/(1 + sum60(volume * hlc3 where hlc3 rose) / sum60(volume * hlc3 where hlc3 fell)). Entry on the first bar where blueWave and moneyFlow are > 0 and rising, close > EMA50 and EMA200 and flat, unless the same condition (without the flat test)
held on the previous bar; fills at the next open. The stop is the lowest low of 10 bars, issued with the entry and re-issued while a position exists (works from the next bar); a close < EMA50 while long exits at the next open."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, np_rsi, np_stoch, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "or1ck5tk"


def check():
    df = bars(9000, seed=450)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    hl3 = (h + l + c) / 3
    n1 = np_ema(hl3, 10)
    n2 = np_ema(np.abs(hl3 - n1), 10)
    tci = np_ema((hl3 - n1) / (0.015 * n2), 21)
    comb = (np_rsi(c, 14) + np_stoch(c, h, l, 14)) / 2
    bw = np_ema(comb, 6) - np_ema(comb, 35) + tci / 2
    d = np.r_[np.nan, np.diff(hl3)]
    up = pd.Series(np.where(d > 0, v * hl3, 0.0)).where(~np.isnan(d)).rolling(60).sum().to_numpy()
    dn = pd.Series(np.where(d < 0, v * hl3, 0.0)).where(~np.isnan(d)).rolling(60).sum().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        mfi = 100 - 100 / (1 + up / dn)
    mf = np_ema(mfi - 50, 5) * 0.8
    e50, e200 = np_ema(c, 50), np_ema(c, 200)
    ss = pd.Series(l).rolling(10).min().to_numpy()
    sh = lambda x, k: np.r_[[np.nan] * k, x[:-k]]
    with np.errstate(invalid="ignore"):
        base = (bw > 0) & (mf > 0) & (bw - sh(bw, 1) > 0) & (mf - sh(mf, 1) > 0) & (c > e200) & (c > e50)
        prev = (sh(bw, 1) > 0) & (sh(mf, 1) > 0) & (sh(bw, 1) - sh(bw, 2) > 0) & (sh(mf, 1) - sh(mf, 2) > 0) & (sh(c, 1) > sh(e200, 1)) & (sh(c, 1) > sh(e50, 1))
    cur = [np.nan]

    def orders(i, pos):
        out = []
        if base[i] and pos == 0 and not prev[i]:
            out.append(("entry", 1))
            cur[0] = ss[i]
        elif pos > 0:
            cur[0] = ss[i]
        with np.errstate(invalid="ignore"):
            if pos > 0 and c[i] < e50[i]:
                out.append(("close", 1))
        return out

    def stop(i, pos, ep, eb):
        return None if np.isnan(cur[0]) else cur[0]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
