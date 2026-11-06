"""Independent check — 3Commas DCA bot (0wggzSk5): 1h continuous bars, orders at the bar close (process_orders_on_close), slippage 0, RSI Less Than 45 and the backtest window widened to the whole sample (passed to both sides). Custom lot-weighted reference (the shared brokers use 1 unit per trade):
the 240-minute RSI14 of 09:30-NY blocks (lookahead off) < 45 with no trade open buys 500/close; the base entry price is the first lot's fill; while in a trade and fewer than 5 averaging orders were placed, a close at or below base * (1 - dev%) adds size/close (devs 2/5/9.5/16/25 %, sizes 900/1620/2916/5249/9448),
at most 6 lots; a close at or above the lot-weighted average * (1 + 3.0%) closes every lot at the bar close (a lot added on the same bar is closed with the rest). Trades are the individual lots, oldest first."""
import numpy as np

from indep import bars, compare, np_periods, np_rsi, np_security_lookahead_off, run_conversion
from pinelib import SymbolInfo
import pandas as pd

TV_ID = "0wggzSk5"
TP = 3.0
DEV = [2.0, 5.0, 9.5, 16.0, 25.0]
SZ = [900.0, 1620.0, 2916.0, 5249.0, 9448.0]


def check():
    df = bars(12000, seed=410, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    pid, last_of = np_periods(df, 240)
    pcl = np.array([c[last_of & (pid == k)][0] for k in range(pid[-1] + 1)])
    rsi = np_security_lookahead_off(np_rsi(pcl, 14), pid, last_of)
    lots, trades = [], []
    prev_pos, base, aof = 0.0, np.nan, 0
    for i in range(n):
        pos = sum(q for q, _, _ in lots)
        inpos = pos != 0
        pending_entries, close_all = [], False
        if prev_pos == 0 and inpos and np.isnan(base):
            base = sum(q * p for q, p, _ in lots) / pos
            aof = 0
        if (prev_pos != 0 and not inpos) or not inpos:
            base, aof = np.nan, 0
        with np.errstate(invalid="ignore"):
            if (not inpos) and rsi[i] < 45.0:
                pending_entries.append(500.0 / c[i])
            if inpos and aof < 5 and not np.isnan(base):
                if c[i] <= base * (1.0 - DEV[aof] / 100.0):
                    pending_entries.append(SZ[aof] / c[i])
                    aof += 1
        if inpos:
            avg = sum(q * p for q, p, _ in lots) / pos
            if c[i] >= avg * (1.0 + TP / 100.0):
                close_all = True
        for q in pending_entries:
            if len(lots) < 6:
                lots.append((q, c[i], i))
        if close_all:
            for q, p, b in lots:
                trades.append((1, b, p, i, c[i]))
            lots = []
        prev_pos = pos
    t0 = int(pd.Timestamp("2015-01-01", tz="UTC").value // 1_000_000)
    t1 = int(pd.Timestamp("2099-01-01", tz="UTC").value // 1_000_000)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", params={"RSI Less Than": 45.0, "From": t0, "To": t1},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), trades)
    return ok and len(trades) > 5, f"{detail} (need >5 trades, got {len(trades)})"
