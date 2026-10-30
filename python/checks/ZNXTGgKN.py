"""Independent check — 3Commas RSI Short (ZNXTGgKN): 15-minute continuous bars, orders at the bar close (process_orders_on_close), slippage 0, backtest window widened to the whole sample (passed to both sides). Lot-based reference (indep.simulate_dca; the shared brokers use 1 unit per trade):
the 240-minute RSI14 crossing DOWN through the level on UTC 4-hour blocks (lookahead off) with no trade open places the base order of 200 quote units (market lot at the signal close, or a pending LIMIT order at the signal close that is replaced on every signal bar and fills at the open when the open crosses down the limit, else when the low reaches it);
the first lot's fill price is the base price; while in a trade and fewer than N averaging orders were placed, a close at or below base * (1 - cumulative deviation) adds size/close (deviations: first step, then each step times the step multiplier, accumulated; sizes: first size times the size multiplier^(k-1));
a close at or above the average * (1 + stop%) closes every lot; once a close is at or below the average * (1 - TP%) the lowest close is tracked (kept until flat) and a close at or above it * (1 + trail%) closes every lot at the bar close (a lot added on the same bar is closed with the rest). Trades are the individual lots, oldest first.
Variants: defaults; market base, 2 averaging orders, level 70, geometric steps; TP 0.8%, trail 0.5%, stop 3%, size multiplier 1.5."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_periods, np_rsi, np_security_lookahead_off, run_conversion, simulate_dca
from pinelib import SymbolInfo

TV_ID = "ZNXTGgKN"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    pid, last_of = np_periods(df, 3, start_minutes=0, tz="UTC")
    pc = c[last_of]
    r = np_rsi(pc, 9)
    with np.errstate(invalid="ignore"):
        xd = np.r_[False, (r[1:] < p["lvl"]) & (r[:-1] >= p["lvl"])]
    sig = np_security_lookahead_off(xd.astype(float), pid, last_of) == 1

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
    def rule(i, avg, S):
        if c[i] >= avg * (1.0 + p["sl"] / 100.0):
            return True
        if c[i] <= avg * (1.0 - p["tp"] / 100.0):
            S["z"] = True
            S["m"] = c[i] if "m" not in S else min(S["m"], c[i])
        return bool(S.get("z") and c[i] >= S["m"] * (1.0 + p["tr"] / 100.0))

    trades = simulate_dca(o, h, l, c, d=-1, sig=sig, win=np.ones(n, bool), base_size=500.0, limit_base=p["lim"], ao_count=p["aoc"], dev=dev, size=size,
                          exit_rule=rule)
    t0 = int(pd.Timestamp("2015-01-01", tz="UTC").value // 1_000_000)
    t1 = int(pd.Timestamp("2099-01-01", tz="UTC").value // 1_000_000)
    sym = SymbolInfo.make("BINANCE:XYZUSDT", "crypto", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="3", params={**params, "From": t0, "To": t1},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "commission_value": 0}), trades)
    return ok and len(trades) > 8, f"{detail} (need >8 trades, got {len(trades)})"


BASE = dict(lvl=80.0, lim=True, aoc=3, asz=250.0, step=1.0, smult=1.0, zmult=1.0, tp=1.3, tr=0.3, sl=8.0)


def check():
    df = bars(40000, seed=21, freq="3min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.6
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Use LIMIT for Base (else Market)": False, "Averaging Orders per Trade": 2, "RSI Crossing Down Level": 70.0, "Deviation to First AO (%)": 0.7, "Deviation Step Multiplier": 1.5},
              dict(lim=False, aoc=2, lvl=70.0, step=0.7, smult=1.5)),
             ({"Take Profit (%)": 0.8, "Trailing (%)": 0.5, "Stop Loss (%)": 3.0, "Order Size Multiplier": 1.5},
              dict(tp=0.8, tr=0.5, sl=3.0, zmult=1.5)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
