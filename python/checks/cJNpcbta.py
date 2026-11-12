"""Independent check — Hybrid VWAP+RSI Strategy (cJNpcbta): 15-minute bars (24 h synthetic, price ~100) of a stock-style symbol with a 1.0 tick and a SPY-like series through the data provider, the script's own risk-based fractional quantities (equity mirrored: initial capital + closed P&L + open P&L, floored to 1e-9), commission / slippage off.
The cumulative hl2 x volume VWAP from the first bar (the one-time `var bool newSession`), RSI(14), ATR(14) / close > 1 %, the SPY daily close over its daily SMA(200) (lookahead off; a na flag is false), the long / short conditions, the risk-sized entry every signal bar (ignored while in a position) and the trailing-stop exit order (activation ATR x 2 or x 1 ticks, offset 0.5 ATR ticks) re-issued on every signal bar are restated bar by bar.
Uses the quantity-aware bracket reference (indep.simulate_brackets with trailing legs). Variants: defaults; trend filter off with RSI 55 / 45 (outside the input range, to get enough trades); trend filter on with RSI 55 / 45."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_periods, np_rsi, np_security_lookahead_off, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "cJNpcbta"
TICK = 1.0


def rq(q, step=1e-9):
    n = q / step
    return np.floor(n + max(1e-9, abs(n) * 1e-12)) * step


def one(df, spy, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    hl2 = (h + l) / 2
    cpv, cv = np.cumsum(hl2 * v), np.cumsum(v)
    vwap = cpv / cv
    pid, last_of = np_periods(df, 1440)
    sc = pd.Series(spy["close"].to_numpy()).groupby(pid).last().to_numpy()
    ssma = np_sma(sc, 200)
    flag = np.where(np.isnan(ssma), 0.0, (sc > ssma).astype(float))
    mt_arr = np_security_lookahead_off(flag, pid, last_of)
    atr, rsi = np_atr(h, l, c, 14), np_rsi(c, 14)
    log: list = []

    def orders(i, info):
        out = []
        eq = 1_000_000.0 + sum(d * (xp - ep) * q for d, _, ep, _, xp, q in log) + sum(x["d"] * x["q"] * (c[i] - x["ep"]) for x in info["lots"])
        mt = bool(mt_arr[i] == 1.0) if p["trend"] else True
        with np.errstate(invalid="ignore", divide="ignore"):
            hv = atr[i] / c[i] > 0.01
            lc = bool(mt and c[i] < vwap[i] and rsi[i] < p["os"] and hv)
            sh = bool((not mt) and c[i] > vwap[i] and rsi[i] > p["ob"] and hv)
            qty = rq(eq * 0.01 / (atr[i] * (2.0 if mt else 1.0)))
        if lc:
            out.append(("entry", "Long", 1, float(qty)))
            out.append(("exit", "Long Exit", "Long", None, None, None, atr[i] * (2 if mt else 1), None, atr[i] * 0.5))
        if sh:
            out.append(("entry", "Short", -1, float(qty)))
            out.append(("exit", "Short Exit", "Short", None, None, None, atr[i] * (2 if mt else 1), None, atr[i] * 0.5))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=TICK, qty_step=1e-9, log=log)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", mintick=TICK, qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, data_provider=lambda s, tf: spy,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


def make(seed, pw):
    df = bars(40000, seed=seed, freq="15min")
    lc = np.log(df["close"].to_numpy() / 100)
    det = lc - np.polyval(np.polyfit(np.arange(len(lc)), lc, 1), np.arange(len(lc)))
    rel = {k: df[k].to_numpy() / df["close"].to_numpy() for k in ("open", "high", "low", "close")}
    for k in rel:
        df[k] = 100 * np.exp(pw * det) * rel[k]          # drift-free, per-bar moves of about 1.7 %
    return df


def check():
    df, spy = make(5, 0.3), make(6, 0.3)
    msgs, allok = [], True
    cases = (({}, dict(trend=True, os=32, ob=68)),
             ({"Use Trend Filter (SPY 200MA)": False, "RSI Oversold (Long)": 55, "RSI Overbought (Short)": 45}, dict(trend=False, os=55, ob=45)),
             ({"RSI Oversold (Long)": 55, "RSI Overbought (Short)": 45}, dict(trend=True, os=55, ob=45)))
    for params, ov in cases:
        ok, m = one(df, spy, params, ov)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
