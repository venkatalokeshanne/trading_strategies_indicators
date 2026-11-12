"""Independent check — Daybreak Strategy (MtKHXU6w): hourly bars (24 h synthetic, price ~100, tick 0.01) of a stock-style symbol (daily periods from 09:30 New York), pending stop orders, quantity 1, commission / slippage / margin off.
The opening range = high / low of the first bar whose New York hour is 9 (the 09:00 bar), cleared at the daily-period change (10:00 bar, which belongs to the new trading day). While no orders were placed since the clear and a range exists, a buy-stop (range high + ATR x sensitivity) and a sell-stop (range low - ATR x sensitivity) with exits (profit / loss in ticks from the fill) are placed once;
they persist until filled (a fill of the other side reverses) and are cancelled at the 21:30 - 22:00 hour bar on weekdays. Uses the quantity-aware bracket reference (indep.simulate_brackets with stop entries and tick-form exits), comparing quantities too. Variants: defaults on a long sample; sensitivity 0.2 with 20 / 15 ticks; sensitivity 1.0 with 80 / 50 ticks."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_periods, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "MtKHXU6w"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    hr = ny.dt.hour.to_numpy()
    mins = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    wd = ny.dt.dayofweek.to_numpy() < 5
    endsess = (mins >= 1290) & (mins < 1320) & wd
    pid, _ = np_periods(df, 1440)
    atr = np_atr(h, l, c, 14)
    S = dict(hi=np.nan, lo=np.nan, placed=False)

    def orders(i, info):
        out = []
        if i > 0 and pid[i] != pid[i - 1]:
            S.update(hi=np.nan, lo=np.nan, placed=False)
        if hr[i] == 9 and np.isnan(S["hi"]):
            S["hi"], S["lo"] = h[i], l[i]
        if not S["placed"] and not np.isnan(S["hi"]):
            out += [("entry", "Long", 1, 1.0, S["hi"] + atr[i] * p["sens"], None), ("exit", "Exit Long", "Long", None, None, None, None, None, None, p["tp"], p["sl"]),
                    ("entry", "Short", -1, 1.0, S["lo"] - atr[i] * p["sens"], None), ("exit", "Exit Short", "Short", None, None, None, None, None, None, p["tp"], p["sl"])]
            S["placed"] = True
        if endsess[i]:
            out += [("cancel", "Long"), ("cancel", "Short")]
        return out

    ref = simulate_brackets(o, h, l, c, orders, tick=0.01)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(sens=0.5, tp=40, sl=25)


def check():
    df = bars(30000, seed=701, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.1
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Sensitivity": 0.2, "Take Profit (in ticks)": 20, "Stop Loss (in ticks)": 15}, dict(sens=0.2, tp=20, sl=15)),
             ({"Sensitivity": 1.0, "Take Profit (in ticks)": 80, "Stop Loss (in ticks)": 50}, dict(sens=1.0, tp=80, sl=50)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
