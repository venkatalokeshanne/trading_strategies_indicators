"""Independent check — RSI Doubling DCA Long (XuFsLXAW): 15-minute continuous bars, orders at the bar close (process_orders_on_close), slippage 0, backtest window widened to the whole sample (passed to both sides). Lot-based reference (indep.simulate_dca; the shared brokers use 1 unit per trade):
the 240-minute RSI of UTC blocks (lookahead off) < level with no trade open places the base order of 200 quote units (market lot at the signal close, or a pending LIMIT order at the signal close that is replaced on every signal bar and fills at the open when the open is below the limit, else when the low reaches it);
the first lot's fill price is the base price; while in a trade and fewer than N averaging orders were placed, a close at or below base * (1 - fixed deviation k) adds size k / close;
a close at or above the lot-weighted average * (1 + TP%) closes every lot at the bar close (a lot added on the same bar is closed with the rest). Trades are the individual lots, oldest first.
Variants: defaults; limit base order, 2 averaging orders, RSI level 52, wider steps; TP 1%, multipliers 1.0."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_periods, np_rsi, np_security_lookahead_off, run_conversion, simulate_dca
from pinelib import SymbolInfo

TV_ID = "XuFsLXAW"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    pid, last_of = np_periods(df, 240, start_minutes=0, tz="UTC")
    pc = c[last_of]
    rsi = np_security_lookahead_off(np_rsi(pc, 14), pid, last_of)
    with np.errstate(invalid="ignore"):
        sig = rsi < p["lvl"]

    dev = lambda k: p["devs"][k - 1]
    size = lambda k: p["sizes"][k - 1]
    trades = simulate_dca(o, h, l, c, d=1, sig=sig, win=np.ones(n, bool), base_size=500.0, limit_base=p["lim"], ao_count=p["aoc"], dev=dev, size=size,
                          exit_rule=lambda i, avg, S: c[i] >= avg * (1.0 + p["tp"] / 100.0))
    t0 = int(pd.Timestamp("2015-01-01", tz="UTC").value // 1_000_000)
    t1 = int(pd.Timestamp("2099-01-01", tz="UTC").value // 1_000_000)
    sym = SymbolInfo.make("BINANCE:SOLUSDT", "crypto", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="240", params={**params, "From": t0, "To": t1},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "commission_value": 0}), trades)
    return ok and len(trades) > 8, f"{detail} (need >8 trades, got {len(trades)})"


BASE = dict(lvl=28.0, lim=False, aoc=5, devs=[2.0, 5.0, 9.5, 16.0, 25.0], sizes=[1000.0, 2000.0, 4000.0, 8000.0, 16000.0], tp=3.0)


def check():
    df = bars(60000, seed=21, freq="240min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.6
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Use LIMIT for Base (else Market)": True, "RSI Less Than": 45.0, "AO1 Deviation from Base (%)": 1.0, "Take Profit (%)": 1.5},
              dict(lim=True, lvl=45.0, devs=[1.0] + BASE["devs"][1:], tp=1.5)),
             ({"RSI Less Than": 55.0, "AO2 Deviation from Base (%)": 3.0, "AO1 Size (USDT)": 700.0},
              dict(lvl=55.0, devs=[BASE["devs"][0], 3.0] + BASE["devs"][2:], sizes=[700.0] + BASE["sizes"][1:])))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
