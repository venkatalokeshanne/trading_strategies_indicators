"""Independent check — BTC Trend Strategy V2 (RI4hNH51): hourly bars, mintick 0.5 (so the trail amounts of ATR read as ticks are ~0.5 ATR, passed to both sides). Trend: close vs the 240-minute EMA200 (plain-pandas blocks from
09:30, lookahead off) with EMA21 vs EMA55; ADX14 > 20, ATR14 > SMA20(ATR), +DI > -DI (short mirrored), pullback to EMA21 and close beyond it, RSI > 55 (< 45) enters (reversing). While a position is open at a close:
stop = entry -/+ 1.8 ATR, trail_points = 1.5 ATR and trail_offset = 1 ATR in ticks, from that close's ATR (works from the next bar); a trend flip closes at the next open. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_adx, np_atr, np_dmi, np_ema, np_periods, np_rsi, np_security_lookahead_off, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "RI4hNH51"
TICK = 0.5


def check():
    df = bars(40000, seed=304, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    pid, last_of = np_periods(df, 240)
    hc = pd.Series(c).groupby(pid).last().to_numpy()
    htf = np_security_lookahead_off(np_ema(hc, 200), pid, last_of)
    f, s, rsi, atr = np_ema(c, 21), np_ema(c, 55), np_rsi(c, 14), np_atr(h, l, c, 14)
    pdi, mdi, adx = np_dmi(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        bull, bear = (c > htf) & (f > s), (c < htf) & (f < s)
        strong, hv = adx > 20, atr > np_sma(atr, 20)
        lc = bull & strong & hv & (pdi > mdi) & (l <= f) & (c > f) & (rsi > 55)
        sc = bear & strong & hv & (mdi > pdi) & (h >= f) & (c < f) & (rsi < 45)
    poscl = np.zeros(n)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if lc[i] and pos <= 0:
            out.append(("entry", 1))
        if sc[i] and pos >= 0:
            out.append(("entry", -1))
        if pos > 0 and bear[i]:
            out.append(("close", 1))
        if pos < 0 and bull[i]:
            out.append(("close", -1))
        return out

    def ok_bar(i, pos):
        return i > 0 and poscl[i - 1] == pos and not np.isnan(atr[i - 1])

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders,
                       stop=lambda i, pos, ep, eb: ep - pos * atr[i - 1] * 1.8 if ok_bar(i, pos) else None,
                       trail=lambda i, pos, ep, eb: (atr[i - 1] * 1.5, atr[i - 1]) if ok_bar(i, pos) else None, tick=TICK)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9, mintick=TICK)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
