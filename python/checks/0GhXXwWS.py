"""Independent check — Advanced DCA Bot (0GhXXwWS): hourly bars of a crypto-style symbol, market orders at the next open, the strategy's own quantities (100, then 100 x multiplier^step), pyramiding 20, commission / slippage / margin off.
RSI crossing under the oversold level while flat opens the initial long; while long and fewer than the maximum steps were used, a close at or below last entry close x (1 - drop) adds a long of base x multiplier^step (the step counter and last entry close are the script's variables); the position closes in full once the close reaches the average price (at the start of the bar) x (1 + TP).
Uses the quantity-aware bracket reference (indep.simulate_brackets, quantities compared too). Variants: defaults with RSI 45; 2 % drop, 2 steps, multiplier 2, TP 1.5 %; RSI length 7 / level 40, 3 % drop, TP 2 %."""
import numpy as np

from indep import bars, compare_q, np_cross_under, np_rsi, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "0GhXXwWS"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    rsi = np_rsi(c, p["rl"])
    xu = np_cross_under(rsi, p["os"])
    S = dict(last=np.nan, cnt=0)

    def orders(i, info):
        out = []
        pos, avg = info["pos"], info["avg"]
        if xu[i] and pos == 0:
            out.append(("entry", "Initial_Entry", 1, 100.0))
            S.update(last=c[i], cnt=0)
        if pos > 0 and S["cnt"] < p["max"]:
            if c[i] <= S["last"] * (1 - p["drop"]):
                S["cnt"] += 1
                out.append(("entry", "DCA_%d" % S["cnt"], 1, 100.0 * p["mult"] ** S["cnt"]))
                S["last"] = c[i]
        if pos > 0 and c[i] >= avg * (1 + p["tp"]):
            out.append(("close_all",))
            S.update(cnt=0, last=np.nan)
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=20)
    sym = SymbolInfo.make("BINANCE:XYZUSDT", "crypto", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(rl=14, os=30, drop=0.05, mult=1.5, max=5, tp=0.03)


def check():
    df = bars(30000, seed=261, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({"RSI Oversold Level": 45}, dict(os=45)),
             ({"RSI Oversold Level": 45, "Price Drop to Trigger DCA (%)": 2.0, "Maximum DCA Steps": 2, "DCA Multiplier (Size of next buy)": 2.0, "Take Profit % from Average Price": 1.5},
              dict(os=45, drop=0.02, max=2, mult=2.0, tp=0.015)),
             ({"RSI Length": 7, "RSI Oversold Level": 40, "Price Drop to Trigger DCA (%)": 3.0, "Take Profit % from Average Price": 2.0}, dict(rl=7, os=40, drop=0.03, tp=0.02)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
