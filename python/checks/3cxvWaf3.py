"""Independent check — ES 3m Momentum (3cxvWaf3): 5-min continuous bars, slippage 0, margin off. EMA8 crossing EMA21 with close vs EMA50, EMA3 of RSI14 vs 50, MACD(8, 21, 3) line vs signal and volume > 1.2 x SMA20 inside 08:30-15:00 Chicago (bar start) flips the position at the next open
(the opposite side is closed first). While a position exists (as of a bar's close) a limit at the position average price +/- 1 point is issued for the trade of its own direction from the next bar. Any position is closed at bars starting 15:00-15:05 Chicago."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "3cxvWaf3"


def check():
    df = bars(16000, seed=150, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    ch = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/Chicago")
    mins = (ch.dt.hour * 60 + ch.dt.minute).to_numpy()
    rth = (mins >= 510) & (mins < 900)
    eod = (mins >= 900) & (mins < 905)
    f, s, t = np_ema(c, 8), np_ema(c, 21), np_ema(c, 50)
    rsi = np_ema(np_rsi(c, 14), 3)
    macd = np_ema(c, 8) - np_ema(c, 21)
    sig = np_ema(macd, 3)
    with np.errstate(invalid="ignore"):
        vol = v > np_sma(v, 20) * 1.2
        le = np_cross_over(f, s) & (c > t) & (rsi > 50) & (macd > sig) & vol & rth
        se = np_cross_under(f, s) & (c < t) & (rsi < 50) & (macd < sig) & vol & rth
    tmp, lv = {}, {}

    def orders(i, pos):
        out = []
        if le[i]:
            out += [("close", -1), ("entry", 1)]
        if se[i]:
            out += [("close", 1), ("entry", -1)]
        lv[i] = (1 if pos > 0 else -1, tmp.get(i)) if pos != 0 and tmp.get(i) is not None else None
        if eod[i] and pos != 0:
            out.append(("close", 1 if pos > 0 else -1))
        return out

    def stop(i, pos, ep, eb):
        tmp[i] = ep
        return None

    def target(i, pos, ep, eb):
        p = lv.get(i - 1) if i > 0 else None
        if p is None or p[0] * pos <= 0:
            return None
        return p[1] + 1.0 if pos > 0 else p[1] - 1.0

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
