"""Independent check — 2AM Night Edge (FP0eD6T3): 15-minute bars (prices x20 so the 6-point target / 30-point stop are meaningful) on a micro-futures symbol (tick 0.25, $5 per point), New York clock, one position, qty 1, market entries at the next open. Window: bars starting 02:00-03:00 inclusive on Monday-Friday; EMA5 crosses EMA13 with RSI14 in (40, 60) [long also needs RSI < 50 with the short bias]; flat, fewer than 3 trades that
calendar day (counter reset at the first bar of each New York date) and the day's closed P&L (x $5) above -$300. Bracket from the first script run with the position (works from the next bar): loss = 120 ticks (30 points), profit = 24 ticks (6 points) from the entry price. From 03:00 on any position is closed at the next open. Variants: default; tight daily loss limit ($100). Commission / slippage / margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "FP0eD6T3"


def one(df, params, dloss):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    f, s = np_ema(c, 5), np_ema(c, 13)
    rsi = np_rsi(c, 14)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    dow = ny.dt.dayofweek.to_numpy()
    dom = ny.dt.day.to_numpy()
    with np.errstate(invalid="ignore"):
        ls = np_cross_over(f, s) & (rsi < 60) & (rsi > 40) & (rsi < 50)
        ss = np_cross_under(f, s) & (rsi > 40) & (rsi < 60)
    sess = (m >= 120) & (m <= 180)
    at_close = m >= 180
    S = dict(tt=0, open_pnl=0.0, last=0)
    log: list = []
    poscl = np.zeros(n)
    sl_arr, tp_arr = np.full(n, np.nan), np.full(n, np.nan)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        net = sum((t[4] - t[2]) * t[0] * 5.0 for t in log)
        if dom[i] != S["last"]:
            S.update(tt=0, open_pnl=net, last=dom[i])
        dpnl = net - S["open_pnl"]
        can = sess[i] and dow[i] < 5 and S["tt"] < 3 and dpnl > -dloss and pos == 0 and not at_close[i]
        if can and ls[i]:
            out.append(("entry", 1))
            S["tt"] += 1
        if can and ss[i]:
            out.append(("entry", -1))
            S["tt"] += 1
        if pos != 0:
            sl_arr[i], tp_arr[i] = 30.0, 6.0
        if at_close[i] and pos != 0:
            out.append(("close", pos))
        return out

    stop = lambda i, pos, ep, eb: None if (i == 0 or eb >= i or poscl[i - 1] * pos <= 0) else ep - pos * 30.0
    tgt = lambda i, pos, ep, eb: None if (i == 0 or eb >= i or poscl[i - 1] * pos <= 0) else ep + pos * 6.0
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt, log=log)
    sym = SymbolInfo.make("CME_MINI:MES1!", "futures", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "commission_value": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(60000, seed=901, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = df[k] * 20.0
    msgs, allok = [], True
    for params, dl in (({}, 300.0), ({"Daily Loss Limit ($)": 100.0}, 100.0)):
        ok, m = one(df, params, dl)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
