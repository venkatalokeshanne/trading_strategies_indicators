"""Independent check — MNQ 09:30 Breakout (bmNIcnn1): 5-minute bars (24h synthetic, returns compressed 10x so the 0.3 % stop test passes), New York clock, one position, market entries at the next open. The bar starting 09:30 sets anchor high / low and resets the day counters; before that
(a previous anchor existing) the day's closed P&L decides the loss streak (two losing days in a row -> skip the new day, streak reset). Window = bars starting 09:31-11:30. A close beyond an anchor with the previous close on the other side, when flat, under 3 trades, not skipped, with (close - anchor low) / close x 100 <= 0.3 (shorts mirrored) and
the direction different from the last trade's, enters; stop = the opposite anchor, target = close +/- 0.10 %, placed with the entry (work from the fill bar). Bars after 11:30 close any position at the next open. Commission / slippage / margin off on the pinelib side (net profit = price difference x 1)."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "bmNIcnn1"


def check():
    df = bars(60000, seed=751, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100.0 * (df[k] / 100.0) ** 0.1
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    S = dict(ah=np.nan, al=np.nan, set=False, tt=0, skip=False, last=0, cl=0, eq=0.0)
    lev = {}
    log: list = []

    def orders(i, pos):
        out = []
        net = sum((t[4] - t[2]) * t[0] for t in log)
        if m[i] == 570:
            if S["set"]:
                if net - S["eq"] < 0:
                    S["cl"] += 1
                else:
                    S["cl"] = 0
            S["skip"] = S["cl"] >= 2
            if S["cl"] >= 2:
                S["cl"] = 0
            S["ah"], S["al"], S["set"], S["tt"], S["last"], S["eq"] = h[i], l[i], True, 0, 0, net
        ok = S["set"] and not S["skip"] and S["tt"] < 3 and pos == 0 and 571 <= m[i] <= 690
        pc = c[i - 1] if i else np.nan
        if ok and c[i] > S["ah"] and pc <= S["ah"] and S["last"] != 1:
            if (c[i] - S["al"]) / c[i] * 100 <= 0.3:
                S["tt"] += 1
                S["last"] = 1
                out.append(("entry", 1))
                lev[i] = (S["al"], c[i] * (1 + 0.1 / 100))
        if ok and c[i] < S["al"] and pc >= S["al"] and S["last"] != -1:
            if (S["ah"] - c[i]) / c[i] * 100 <= 0.3:
                S["tt"] += 1
                S["last"] = -1
                out.append(("entry", -1))
                lev[i] = (S["ah"], c[i] * (1 - 0.1 / 100))
        if m[i] > 690 and pos != 0:
            out.append(("close", pos))
        return out

    stop = lambda i, pos, ep, eb: lev[eb - 1][0] if eb - 1 in lev else None
    tgt = lambda i, pos, ep, eb: lev[eb - 1][1] if eb - 1 in lev else None
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt, log=log)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "commission_value": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"
