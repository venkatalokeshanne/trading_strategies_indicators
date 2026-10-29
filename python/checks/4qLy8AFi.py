"""Independent check — Dual MA Crossover + Volatility Filter (4qLy8AFi): 15-minute bars (24h synthetic) on a stock chart (trading day from 09:30 New York), one position, trade list only, market orders at the next open. EMA20 crosses EMA50 (HMA variant too),
ATR14 > ATR20, RSI14 beyond 50 and at least 6 bars since the day's first bar (counter reset on each new day; bar 0 counts 1). While in a trade, at every script run: the best price since the signal close, run = (best - signal close) / (2 x ATR now);
at 1R the stop jumps to the signal close and from then on trails best -/+ 3 ATR (ratchet); a time exit (>= 10 bars since the signal and the 10-bar high / low [fed only on bars with the position] is not above / below the previous bar's value of that call) closes at the next open. The stop order
(initial stop = signal close -/+ 2 ATR) is issued from the first script run that sees the position (so it works from the bar after the fill). Variants: default and HMA. Slippage / margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_ema, np_rsi, np_wma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "4qLy8AFi"


def hma(x, n):
    return np_wma(2 * np_wma(x, n // 2) - np_wma(x, n), int(np.floor(np.sqrt(n))))


def one(df, params, ma):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    fa, sl = ma(c, 20), ma(c, 50)
    atr, atrc, rsi = np_atr(h, l, c, 14), np_atr(h, l, c, 20), np_rsi(c, 14)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    day = (ny.dt.tz_localize(None) - pd.Timedelta(minutes=9 * 60 + 30)).dt.date.to_numpy()
    bso = np.zeros(n)
    for i in range(n):
        bso[i] = 0 if (i > 0 and day[i] != day[i - 1]) else (bso[i - 1] if i else 0) + 1
    with np.errstate(invalid="ignore"):
        lg = np_cross_over(fa, sl) & (atr > atrc) & (rsi > 50) & (bso >= 6)
        sg = np_cross_under(fa, sl) & (atr > atrc) & (rsi < 50) & (bso >= 6)
    S = dict(ep=np.nan, stop=np.nan, be=False, ebi=0, mx=np.nan, mn=np.nan)
    fed_h, fed_l = [], []
    hv, lv = np.full(n, np.nan), np.full(n, np.nan)
    stop_arr = np.full(n, np.nan)

    def orders(i, pos):
        out = []
        sd = atr[i] * 2.0
        if pos == 0 and lg[i]:
            out.append(("entry", 1))
            S.update(ep=c[i], stop=c[i] - sd, be=False, ebi=i, mx=c[i])
        if pos == 0 and sg[i]:
            out.append(("entry", -1))
            S.update(ep=c[i], stop=c[i] + sd, be=False, ebi=i, mn=c[i])
        if pos > 0:
            S["mx"] = max(S["mx"], h[i])
            run = (S["mx"] - S["ep"]) / sd
            if not S["be"] and run >= 1.0:
                S["stop"], S["be"] = S["ep"], True
            if S["be"]:
                S["stop"] = max(S["stop"], S["mx"] - atr[i] * 3.0)
            fed_h.append(h[i])
            hv[i] = max(fed_h[-10:]) if len(fed_h) >= 10 else np.nan
            prev = hv[i - 1] if i else np.nan
            if (i - S["ebi"] >= 10) and hv[i] <= prev:
                out.append(("close", 1))
        if pos < 0:
            S["mn"] = min(S["mn"], l[i])
            run = (S["ep"] - S["mn"]) / sd
            if not S["be"] and run >= 1.0:
                S["stop"], S["be"] = S["ep"], True
            if S["be"]:
                S["stop"] = min(S["stop"], S["mn"] + atr[i] * 3.0)
            fed_l.append(l[i])
            lv[i] = min(fed_l[-10:]) if len(fed_l) >= 10 else np.nan
            prev = lv[i - 1] if i else np.nan
            if (i - S["ebi"] >= 10) and lv[i] >= prev:
                out.append(("close", -1))
        if pos != 0:
            stop_arr[i] = S["stop"]
        return out

    stop = lambda i, pos, ep, eb: None if (eb >= i or np.isnan(stop_arr[i - 1])) else stop_arr[i - 1]
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(30000, seed=571, freq="15min")
    msgs, allok = [], True
    for params, ma in (({}, np_ema), ({"MA Type": "HMA"}, hma)):
        ok, m = one(df, params, ma)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
