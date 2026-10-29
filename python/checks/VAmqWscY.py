"""Independent check — 09:29 NY Limit Reversal (VAmqWscY): 1-minute bars (24 h synthetic, price ~100) on a crypto-style symbol, default quantity 1, commission / slippage / margin off.
At the first bar of each New York calendar day everything pending is cancelled and the state reset. The 09:29 New York bar's close is the reference: a buy limit at reference - offset and a sell limit at reference + offset are placed on bars before 09:35 while flat (once per day), each with an exit order (stop = limit -/+ SL points, take-profit = limit +/- SL x RR);
from 09:35 on, while flat and after the orders were placed, every pending order is cancelled; while a position is open, the pending "Long" / "Short" entries are cancelled at the end of each bar. Limit fills: at the limit price, or at the open when the bar opens beyond it. Uses the quantity-aware bracket reference (indep.simulate_brackets with limit entries and cancels), comparing quantities too.
Variants: defaults scaled to the price (offset 0.3, SL 0.2); offset 0.15, SL 0.1, RR 3; offset 0.5, SL 0.3, RR 1."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "VAmqWscY"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    hhmm = (ny.dt.hour * 100 + ny.dt.minute).to_numpy()
    day = ny.dt.date.to_numpy()
    S = dict(ref=np.nan, bl=np.nan, sl_=np.nan, done=False)

    def orders(i, info):
        out = []
        pos = info["pos"]
        if i > 0 and day[i] != day[i - 1]:
            S.update(ref=np.nan, bl=np.nan, sl_=np.nan, done=False)
            out.append(("cancel_all",))
        if hhmm[i] == 929:
            S["ref"] = c[i]
            S["bl"], S["sl_"] = c[i] - p["off"], c[i] + p["off"]
        if hhmm[i] >= 935 and pos == 0 and S["done"]:
            out.append(("cancel_all",))
        if not np.isnan(S["ref"]) and not S["done"] and hhmm[i] < 935 and pos == 0:
            S["done"] = True
            bl, sl_ = S["bl"], S["sl_"]
            out += [("entry", "Long", 1, 1.0, None, bl), ("exit", "ExL", "Long", None, bl - p["sl"], bl + p["sl"] * p["rr"]),
                    ("entry", "Short", -1, 1.0, None, sl_), ("exit", "ExS", "Short", None, sl_ + p["sl"], sl_ - p["sl"] * p["rr"])]
        if pos != 0:
            out += [("cancel", "Long"), ("cancel", "Short")]
        return out

    ref = simulate_brackets(o, h, l, c, orders)
    sym = SymbolInfo.make("BINANCE:XYZUSDT", "crypto", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="1", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(off=20.0, sl=10.0, rr=2.0)


def check():
    df = bars(60000, seed=241, freq="1min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.08
    msgs, allok = [], True
    cases = (({"掛單距離 (Offset)": 0.3, "止損點數 (SL)": 0.2}, dict(off=0.3, sl=0.2)),
             ({"掛單距離 (Offset)": 0.15, "止損點數 (SL)": 0.1, "盈虧比 (RR)": 3.0}, dict(off=0.15, sl=0.1, rr=3.0)),
             ({"掛單距離 (Offset)": 0.5, "止損點數 (SL)": 0.3, "盈虧比 (RR)": 1.0}, dict(off=0.5, sl=0.3, rr=1.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
