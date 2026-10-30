"""Independent check — Heikin Ashi RSI Fade Short (nuqVC5F7): 15-minute continuous bars on a crypto symbol (15-minute RSI), orders at the bar close (process_orders_on_close), commission / slippage / margin off, backtest window off.
Heikin Ashi candles of the 15-minute bars (close = ohlc4, open = average of the previous HA open and close, first open = (open + close) / 2) give the count of bars since the last non-bullish (non-bearish) candle; with that count >= N and the 15-minute RSI(100) (lookahead off) above (below) its level
and flat, a short base order is placed at the close (market lot at the close, or a limit order at the close, replaced on each signal bar, filled when the next bars reach it); while open, a take-profit limit and a stop-loss stop around the average entry price are issued at each bar close and work from the next bar.
Uses the pending-order reference broker (simulate_ord, on_close). Variants: defaults; RSI Less Than 55 with a bearish streak of 4, limit base order; shorter RSI 14, streak 3, TP 1% / SL 1.5%."""
import numpy as np

from indep import bars, compare, np_periods, np_rsi, np_security_lookahead_off, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "nuqVC5F7"


def barssince(cond):
    out = np.full(len(cond), np.nan)
    last = None
    for i, x in enumerate(cond):
        if x:
            last = i
        if last is not None:
            out[i] = i - last
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    pid, last_of = np_periods(df, 15, start_minutes=0, tz="UTC")
    rsi = np_security_lookahead_off(np_rsi(c[last_of], p["rl"]), pid, last_of)
    hac = (o + h + l + c) / 4.0
    hao = np.empty(n)
    for i in range(n):
        hao[i] = (o[i] + c[i]) / 2.0 if i == 0 else (hao[i - 1] + hac[i - 1]) / 2.0
    bull, bear = barssince(hac <= hao), barssince(hac >= hao)
    cnt = bull if p["dir"] == "Bullish" else bear
    with np.errstate(invalid="ignore"):
        crsi = rsi > p["lvl"] if p["cond"] == "Greater Than" else rsi < p["lvl"]
        sig = crsi & (cnt >= p["streak"])

    def orders(i, pos, info):
        out = []
        if pos == 0 and sig[i]:
            out.append(("entry", "Short_Base", -1, None, c[i] if p["lim"] else None))
        if pos != 0:
            out.append(("exit", "Exit", "Short_Base", info["ep"] * (1.0 + p["sl"] / 100.0), info["ep"] * (1.0 - p["tp"] / 100.0)))
        return out

    ref = simulate_ord(o, h, l, c, orders, on_close=True)
    sym = SymbolInfo.make("BINANCE:XYZUSDT", "crypto", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params={**params, "From": 0, "To": 4102444800000}, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "commission_value": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(rl=100, cond="Greater Than", lvl=46.0, dir="Bullish", streak=7, lim=False, tp=2.1, sl=2.5)


def check():
    df = bars(60000, seed=29, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.6
    msgs, allok = [], True
    cases = (({}, {}),
             ({"RSI Condition": "Less Than", "RSI Level": 55.0, "HA Streak Direction": "Bearish", "Consecutive Candles": 4, "Use LIMIT for Base (else Market)": True},
              dict(cond="Less Than", lvl=55.0, dir="Bearish", streak=4, lim=True)),
             ({"RSI Length": 14, "Consecutive Candles": 3, "Take Profit (%)": 1.0, "Stop Loss (%)": 1.5}, dict(rl=14, streak=3, tp=1.0, sl=1.5)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
