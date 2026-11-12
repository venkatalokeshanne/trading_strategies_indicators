"""Independent check — Multi Long Bot / Triple RSI DCA Long (u4g3IrXS): 5-minute bars (24 h synthetic) on a crypto symbol (UTC period blocks), market orders at the next open, commission / slippage / margin off, one unit per order (pyramiding 4: base + 3 safety orders).
RSI(14) of 15-minute periods, RSI(14) of 30-minute periods and RSI(7) of 5-minute bars, each shown on every chart bar of the NEXT period as the previous completed period's value (lookahead on with [1]); the base order is placed when the 15-minute value crosses above its threshold while no deal is open;
safety order k: when the bar's low reaches base * (1 - step * sum(scale^i)) (up to the maximum) and the 30m or 5m RSI has just crossed above its threshold, with the deal's running average of intended fill prices (min(open, level)) recorded; the deal is closed at the next open when the high reaches the average * (1 + TP) (state cleared at the signal bar).
Uses the multi-trade reference broker (simulate_pyr).
Variants: defaults; threshold 40 / 40 / 40, TP 1%, 2 safety orders; no entry-RSI requirement with safety signals off, step scale 1.2."""
import numpy as np

from indep import bars, compare, np_periods, np_rsi, run_conversion, simulate_pyr
from pinelib import SymbolInfo


TV_ID = "u4g3IrXS"


def prev_rsi(df, minutes, ln):
    pid, last_of = np_periods(df, minutes, start_minutes=0, tz="UTC")
    r = np_rsi(df["close"].to_numpy()[last_of], ln)
    prev = np.r_[np.nan, r[:-1]]
    return prev[pid]


def cross(x, thr):
    px = np.r_[np.nan, x[:-1]]
    with np.errstate(invalid="ignore"):
        return (x > thr) & (px <= thr)


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    e = prev_rsi(df, 15, 14)
    s1 = prev_rsi(df, 30, 14)
    s2 = prev_rsi(df, 5, 7)
    esig = cross(e, p["et"]) if p["ue"] else np.ones(n, bool)
    ssig = (cross(s1, p["t1"]) | cross(s2, p["t2"])) if p["us"] else np.ones(n, bool)
    S = dict(base=np.nan, cost=0.0, qty=0.0, so=0, avg=np.nan)

    def orders(i, pos):
        out = []
        nidx = S["so"] + 1
        if 0 < nidx <= p["mso"]:
            dev = sum(p["scale"] ** j for j in range(nidx)) * p["step"]
            npx = S["base"] * (1.0 - dev) if not np.isnan(S["base"]) else np.nan
        else:
            npx = np.nan
        nusd = 15.075 * p["vs"] ** max(S["so"], 0)
        if pos == 0 and np.isnan(S["base"]) and esig[i]:
            S.update(base=c[i], avg=c[i], cost=20.075, qty=20.075 / c[i], so=0)
            out.append(("entry", 1))
        if pos > 0 and S["so"] < p["mso"] and not np.isnan(npx):
            if l[i] <= npx and ssig[i]:
                ex = min(o[i], npx)
                q = nusd / ex
                out.append(("entry", 1))
                S["cost"] += nusd
                S["qty"] += q
                S["avg"] = S["cost"] / S["qty"]
                S["so"] += 1
        if pos > 0 and not np.isnan(S["avg"]) and h[i] >= S["avg"] * (1.0 + p["tp"]):
            out.append(("close_all",))
            S.update(base=np.nan, avg=np.nan, cost=0.0, qty=0.0, so=0)
        return out

    ref = simulate_pyr(o, h, l, c, orders, pyramiding=4)
    sym = SymbolInfo.make("BINANCE:XYZUSDT", "crypto", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "commission_value": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(et=30.0, t1=30.0, t2=30.0, ue=True, us=True, mso=3, vs=1.9, step=0.01, scale=1.65, tp=0.019)


def check():
    df = bars(40000, seed=3, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.6
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Entry RSI Threshold": 40.0, "SO Sig 1 — RSI Threshold": 40.0, "SO Sig 2 — RSI Threshold": 40.0, "Take Profit % (from AVG)": 1.0, "Max Safety Orders": 2},
              dict(et=40.0, t1=40.0, t2=40.0, tp=0.01, mso=2)),
             ({"Require RSI cross-above for SO entry (OR of two TFs)": False, "Step Scale (martingale)": 1.2, "Entry RSI Threshold": 45.0},
              dict(us=False, scale=1.2, et=45.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
