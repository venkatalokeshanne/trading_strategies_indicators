"""Independent check — Dual RSI DCA Long (qgofvS9I): 15-minute continuous bars, orders at the bar close (process_orders_on_close), slippage 0, backtest window widened to the whole sample (passed to both sides). Lot-based reference (indep.simulate_dca; the shared brokers use 1 unit per trade):
the 3-minute RSI14 (lookahead off) crossing UP its level (previous value of the mapped series) with no trade open places the base order of 200 quote units (market lot at the signal close, or a pending LIMIT order at the signal close that is replaced on every signal bar and fills at the open when the open is below the limit, else when the low reaches it);
the first lot's fill price is the base price; while in a trade and fewer than N averaging orders were placed, a close at or below base * (1 - cumulative deviation) adds size/close (deviations: first step, then each step times the step multiplier, accumulated; sizes: first size times the size multiplier^(k-1));
a close at least the minimum profit above the lot-weighted average together with a second RSI crossing DOWN its level closes every lot at the bar close (a lot added on the same bar is closed with the rest). Trades are the individual lots, oldest first.
Variants: defaults; limit base order, 2 averaging orders, RSI level 52, wider steps; TP 1%, multipliers 1.0."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_periods, np_rsi, np_security_lookahead_off, run_conversion, simulate_dca
from pinelib import SymbolInfo

TV_ID = "qgofvS9I"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    pid, last_of = np_periods(df, 3, start_minutes=0, tz="UTC")
    pc = c[last_of]
    r = np_security_lookahead_off(np_rsi(pc, 14), pid, last_of)
    prev = np.r_[np.nan, r[:-1]]
    with np.errstate(invalid="ignore"):
        sig = (prev < p["lvl"]) & (r >= p["lvl"])
        xdn = (prev > p["xl"]) & (r <= p["xl"])

    def dev(k):
        x, st = 0.0, p["step"]
        for j in range(1, k + 1):
            if j == 1:
                x = st
            else:
                st *= p["smult"]
                x += st
        return x

    size = lambda k: p["asz"] * p["zmult"] ** (k - 1)
    trades = simulate_dca(o, h, l, c, d=1, sig=sig, win=np.ones(n, bool), base_size=90.0, limit_base=p["lim"], ao_count=p["aoc"], dev=dev, size=size,
                          exit_rule=lambda i, avg, S: bool(c[i] >= avg * (1.0 + p["mp"] / 100.0) and xdn[i]))
    t0 = int(pd.Timestamp("2015-01-01", tz="UTC").value // 1_000_000)
    t1 = int(pd.Timestamp("2099-01-01", tz="UTC").value // 1_000_000)
    sym = SymbolInfo.make("BINANCE:SOLUSDT", "crypto", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="3", params={**params, "From": t0, "To": t1},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "commission_value": 0}), trades)
    return ok and len(trades) > 8, f"{detail} (need >8 trades, got {len(trades)})"


BASE = dict(lvl=31.0, xl=69.0, lim=False, aoc=5, asz=110.0, step=1.3, smult=1.3, zmult=1.25, mp=2.4)


def check():
    df = bars(40000, seed=21, freq="3min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.6
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Use LIMIT for Base (else Market)": True, "Averaging Orders per Trade": 3, "RSI Crossing Up Level": 40.0, "Deviation to First AO (%)": 0.8, "Deviation Step Multiplier": 1.5, "Minimum Profit (%)": 1.2},
              dict(lim=True, aoc=3, lvl=40.0, step=0.8, smult=1.5, mp=1.2)),
             ({"RSI Crossing Down Level": 60.0, "Minimum Profit (%)": 0.6, "Order Size Multiplier": 1.0},
              dict(xl=60.0, mp=0.6, zmult=1.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
