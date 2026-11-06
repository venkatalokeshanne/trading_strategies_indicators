"""Independent check — MACD Pullback Sniper (V87nRt9v): daily bars, one position (reversals), trade list only (quantity does not change entries / exits as long as it is positive). MACD(12,26,9) cross over its signal below zero (short:
cross under above zero), close vs EMA200 and ADX14 > 20, from 2018-01-01. Entry at the next open; an exit order is placed with the entry from the signal close (stop = close -/+ 2 ATR14, target 2 x that) and works on the fill bar;
afterwards, while in a position at a script run, it is rebuilt around the position average price with the ATR saved at entry, so bar i works with bar i-1's levels (only if a position existed at bar i-1's script run). An opposite
MACD cross closes the trade unless it is itself an entry signal (then the entry reverses). Margin and slippage off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_dmi, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "V87nRt9v"


def check():
    df = bars(6000, seed=383)
    t = df["time"].to_numpy()
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    macd = np_ema(c, 12) - np_ema(c, 26)
    sig = np_ema(macd, 9)
    ema = np_ema(c, 200)
    adx = np_dmi(h, l, c, 14)[2]
    atr = np_atr(h, l, c, 14)
    bc, sc = np_cross_over(macd, sig), np_cross_under(macd, sig)
    with np.errstate(invalid="ignore"):
        inr = (t >= 1514764800000) & (t <= 3155846340000)
        ls = bc & (c > ema) & (macd < 0) & (adx > 20) & inr
        ss = sc & (c < ema) & (macd > 0) & (adx > 20) & inr
    S = dict(eatr=np.nan, sig=None)
    eatr_hist = np.full(n, np.nan)
    poscl = np.zeros(n)
    avg_at = np.full(n, np.nan)
    ep_now = {"i": -1, "ep": np.nan}

    def orders(i, pos):
        poscl[i] = pos
        if pos != 0 and ep_now["i"] == i:
            avg_at[i] = ep_now["ep"]
        out = []
        if bc[i] and sc[i] == False and pos < 0 and not ls[i]:
            out.append(("close", -1))
        if sc[i] and pos > 0 and not ss[i]:
            out.append(("close", 1))
        if ls[i] and pos <= 0:
            S["eatr"] = atr[i]
            S["sig"] = (1, i, c[i] - atr[i] * 2.0, c[i] + atr[i] * 4.0)
            out.append(("entry", 1))
        if ss[i] and pos >= 0:
            S["eatr"] = atr[i]
            S["sig"] = (-1, i, c[i] + atr[i] * 2.0, c[i] - atr[i] * 4.0)
            out.append(("entry", -1))
        eatr_hist[i] = S["eatr"]
        return out

    # per-bar entry ATR as of that bar's script run (var, set at signals)

    def stop(i, pos, ep, eb):
        ep_now["i"], ep_now["ep"] = i, ep
        sg = S["sig"]
        if eb == i and i > 0 and sg and sg[0] == pos and sg[1] == i - 1:
            return sg[2]
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(avg_at[i - 1]):
            return None
        return avg_at[i - 1] - pos * eatr_hist[i - 1] * 2.0

    def target(i, pos, ep, eb):
        sg = S["sig"]
        if eb == i and i > 0 and sg and sg[0] == pos and sg[1] == i - 1:
            return sg[3]
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(avg_at[i - 1]):
            return None
        return avg_at[i - 1] + pos * eatr_hist[i - 1] * 4.0

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
