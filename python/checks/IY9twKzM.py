"""Independent check — El Doble Double Bollinger (IY9twKzM): 15-min continuous bars, slippage 0, SL / TP 3 / 5 points here (passed to both sides). Bull setup: a bar with low <= BB(20,2) lower (population stdev) happened 1-10 bars ago (barssince in [1, 10]); bull reversal bar: close > open and close > SMA4(close);
trend: close > EMA55 or EMA55 - EMA55[5] > 0; ADX14 > 18; 02:00-09:00 New York (hour); fewer than 3 trades today (trading day = 09:30-NY block), flat. Entry at the next open, stop / target = close -/+ 3 / +/- 5 fixed at the signal. The trade is closed (market) once bar_index - entry signal bar >= 20 while a position exists.
Short mirrors with bear touch on the upper band."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_dmi, np_ema, np_periods, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "IY9twKzM"
SLP, TPP = 3.0, 5.0


def check():
    df = bars(16000, seed=180, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    hr = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York").dt.hour.to_numpy()
    pid, _ = np_periods(df, 1440)
    basis = np_sma(c, 20)
    dev = 2.0 * pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    up, lo = basis + dev, basis - dev
    fb = np_sma(c, 4)
    ema = np_ema(c, 55)
    ema5 = np.r_[[np.nan] * 5, ema[:-5]]
    dp, dm, adx = np_dmi(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        bt, st_ = l <= lo, h >= up
    def since(x):
        out = np.full(n, np.nan)
        last = None
        for i in range(n):
            if x[i]:
                last = i
            out[i] = np.nan if last is None else i - last
        return out
    sb, ss = since(bt), since(st_)
    with np.errstate(invalid="ignore"):
        bs = (sb >= 1) & (sb <= 10)
        ses = (ss >= 1) & (ss <= 10)
        brv, srv = (c > o) & (c > fb), (c < o) & (c < fb)
        btr, str_ = (c > ema) | (ema - ema5 > 0), (c < ema) | (ema - ema5 < 0)
        adxok = adx > 18
    s = dict(n=0, eb=None)
    lvl = {}

    def orders(i, pos):
        out = []
        if i == 0 or pid[i] != pid[i - 1]:
            s["n"] = 0
        sess = 2 <= hr[i] < 9
        can = s["n"] < 3 and sess and pos == 0
        if can and bs[i] and brv[i] and btr[i] and adxok[i]:
            s["eb"] = i
            s["n"] += 1
            out.append(("entry", 1))
            lvl[1] = (c[i] - SLP, c[i] + TPP)
        if can and ses[i] and srv[i] and str_[i] and adxok[i]:
            s["eb"] = i
            s["n"] += 1
            out.append(("entry", -1))
            lvl[-1] = (c[i] + SLP, c[i] - TPP)
        if pos != 0 and s["eb"] is not None and i - s["eb"] >= 20:
            out.append(("close", 1 if pos > 0 else -1))
        return out

    def stop(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][0]

    def target(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params={"Stop Loss Points": SLP, "Take Profit Points": TPP},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
