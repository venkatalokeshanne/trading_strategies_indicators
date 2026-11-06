"""Independent check — HTF Candle Direction (3kv64PEa): 30-min bars, HTF 720 (09:30-NY 12-hour blocks), lookahead ON (each chart bar sees its block's final open / close). Bullish block + close > EMA50 + no signal yet today -> long (bearish -> short), at the next open reversing an open opposite trade;
one signal per trading day (the day rolls at 09:30 NY)."""
import numpy as np

from indep import bars, compare, np_ema, np_periods, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "3kv64PEa"


def check():
    df = bars(12000, seed=120, freq="30min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    pid, last_of = np_periods(df, 720)
    first_of = np.r_[True, pid[1:] != pid[:-1]]
    popen = o[first_of]
    pclose = c[last_of]
    ho, hc = popen[pid], pclose[pid]
    did, _ = np_periods(df, 1440)
    ema = np_ema(c, 50)
    st = dict(active=False)

    def orders(i, pos):
        out = []
        if i > 0 and did[i] != did[i - 1]:
            st["active"] = False
        with np.errstate(invalid="ignore"):
            if hc[i] > ho[i] and c[i] > ema[i] and not st["active"]:
                out.append(("entry", 1))
                st["active"] = True
            if hc[i] < ho[i] and c[i] < ema[i] and not st["active"]:
                out.append(("entry", -1))
                st["active"] = True
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="30", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
