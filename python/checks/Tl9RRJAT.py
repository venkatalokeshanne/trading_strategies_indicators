"""Independent check — RSI Dip + EMA Trend Long DCA (Tl9RRJAT): 15-minute continuous bars, orders at the bar close (process_orders_on_close), slippage 0, backtest window widened to the whole sample (passed to both sides). Lot-based reference (indep.simulate_dca; the shared brokers use 1 unit per trade):
the 5-minute RSI12 crossing DOWN its level (previous value of the series, equal timeframe) while the 15-minute EMA fast > slow (UTC blocks, lookahead off), flat places the base order of 200 quote units (market lot at the signal close, or a pending LIMIT order at the signal close that is replaced on every signal bar and fills at the open when the open is below the limit, else when the low reaches it);
the first lot's fill price is the base price; while in a trade and fewer than N averaging orders were placed, a close at or below base * (1 - cumulative deviation) adds size/close (deviations: first step, then each step times the step multiplier, accumulated; sizes: first size times the size multiplier^(k-1));
a close at or below average * (1 - SL%), a holding time of the max hold (from the first script run in the trade), or the trailing exit (highest close since a close at or above average * (1 + TP%); close at or below peak * (1 - trail%)) closes every lot at the bar close (a lot added on the same bar is closed with the rest). Trades are the individual lots, oldest first.
Variants: defaults; limit base order, 2 averaging orders, RSI level 52, wider steps; TP 1%, multipliers 1.0."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_periods, np_rsi, np_security_lookahead_off, run_conversion, simulate_dca
from pinelib import SymbolInfo

TV_ID = "Tl9RRJAT"


def ema_na(x, n):
    out = np.full(len(x), np.nan)
    idx = np.flatnonzero(~np.isnan(x))
    if len(idx) < n:
        return out
    s = idx[0] + n - 1
    out[s] = x[idx[0]:s + 1].mean()
    k = 2.0 / (n + 1)
    for i in range(s + 1, len(x)):
        out[i] = k * x[i] + (1 - k) * out[i - 1]
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    r5 = np_rsi(c, 12)
    pr = np.r_[np.nan, r5[:-1]]
    pid, last_of = np_periods(df, 15, start_minutes=0, tz="UTC")
    pc = c[last_of]
    ef = np_security_lookahead_off(ema_na(pc, p["ef"]), pid, last_of)
    es = np_security_lookahead_off(ema_na(pc, p["es"]), pid, last_of)
    with np.errstate(invalid="ignore"):
        sig = (pr > p["lvl"]) & (r5 <= p["lvl"]) & (ef > es)
    times = df["time"].to_numpy()

    def dev(k):
        x, st = 0.0, p["step"]
        for j in range(1, k + 1):
            if j == 1:
                x = st
            else:
                st *= p["smult"]
                x += st
        return x

    size = lambda k: p["asz"] * p["zmult"] ** (k - 1) * p["lev"]

    def rule(i, avg, S):
        if "t0" not in S:
            S["t0"] = times[i]
        if c[i] <= avg * (1.0 - p["sl"] / 100.0):
            return True
        if p["mh"] and (times[i] - S["t0"]) >= p["mhs"] * 1000:
            return True
        if c[i] >= avg * (1.0 + p["tp"] / 100.0):
            S["z"] = True
            S["m"] = c[i] if "m" not in S else max(S["m"], c[i])
        return bool(S.get("z") and c[i] <= S["m"] * (1.0 - p["td"] / 100.0))

    trades = simulate_dca(o, h, l, c, d=1, sig=sig, win=np.ones(n, bool), base_size=60.0 * p["lev"], limit_base=p["lim"], ao_count=p["aoc"], dev=dev, size=size,
                          exit_rule=rule)
    t0 = int(pd.Timestamp("2015-01-01", tz="UTC").value // 1_000_000)
    t1 = int(pd.Timestamp("2099-01-01", tz="UTC").value // 1_000_000)
    sym = SymbolInfo.make("BINANCE:SOLUSDT", "crypto", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params={**params, "From": t0, "To": t1},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "commission_value": 0}), trades)
    return ok and len(trades) > 8, f"{detail} (need >8 trades, got {len(trades)})"


BASE = dict(lvl=35.0, ef=50, es=100, lim=False, aoc=4, asz=60.0, step=1.0, smult=1.2, zmult=1.05, lev=25.0, tp=1.0, td=0.1, sl=9.0, mh=True, mhs=259200)


def check():
    df = bars(60000, seed=21, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.6
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Use LIMIT for Base (else Market)": True, "Max Safety Orders": 2, "RSI Crossing Down Level": 45.0, "Fast EMA Length": 20, "Slow EMA Length": 40, "Step to First SO (%)": 0.5},
              dict(lim=True, aoc=2, lvl=45.0, ef=20, es=40, step=0.5)),
             ({"Take Profit (%)": 0.5, "Trailing Deviation (%)": 0.2, "Stop Loss (%)": 2.0, "Max Hold (seconds)": 7200, "Fast EMA Length": 20, "Slow EMA Length": 40, "RSI Crossing Down Level": 45.0},
              dict(tp=0.5, td=0.2, sl=2.0, mhs=7200, ef=20, es=40, lvl=45.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
