"""Independent check — ECV Strategy v2 MGC1! (PRzNz3M7): 5-minute bars (24 h synthetic, price ~2000, 0.1 tick) of a CME futures symbol, market orders at the next open, 2 contracts, commission / slippage / margin off.
Signal: a bar taking both the previous high and low and closing beyond the previous open (colour as the side), volume > 1.3 x the previous bar's, on the right side of EMA50, bars-since-in-position >= cooldown, Asia (20:00 - 03:00 New York) or NY (09:30 - 16:00) window; entry when the script state is idle.
With the entry two exit orders of 1 contract (profit 100 / 200 ticks, loss 50 ticks, from the lot's entry price) are issued; once the close reaches the entry +/- 50 ticks a third order of 1 contract with a zero-tick stop is added (once); the state returns to idle when flat at script time. Uses the quantity-aware bracket reference (indep.simulate_brackets with tick-form exits and quantity exits), comparing quantities too.
Variants: defaults; cooldown 3 with TP 40 / 80, stop 20 ticks."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_ema, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "PRzNz3M7"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    sym = SymbolInfo.make("COMEX:MGC1!", "futures", mintick=0.1, qty_step=1e-9)
    tick = 0.1
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    em = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    sess = ((em >= 570) & (em < 960)) | (em >= 1200) | (em < 180)
    ema = np_ema(c, 50)
    S = dict(bse=999, st="IDLE", buy=False, be=np.nan, hit=False)

    def orders(i, info):
        out = []
        pos = info["pos"]
        S["bse"] = 0 if pos != 0 else S["bse"] + 1
        if i == 0:
            return out
        with np.errstate(invalid="ignore"):
            bull = c[i] > o[i] and h[i] >= h[i - 1] and l[i] <= l[i - 1] and c[i] > o[i - 1]
            bear = c[i] < o[i] and h[i] >= h[i - 1] and l[i] <= l[i - 1] and c[i] < o[i - 1]
            vol = v[i] > v[i - 1] * 1.3
            cool = S["bse"] >= p["cd"]
            buy = bull and vol and c[i] > ema[i] and cool and sess[i]
            sell = bear and vol and c[i] < ema[i] and cool and sess[i]
        if (buy or sell) and S["st"] == "IDLE":
            S.update(buy=bool(buy), st="IN", hit=False, be=c[i] + p["sl"] * tick if buy else c[i] - p["sl"] * tick)
            out += [("entry", "ECV", 1 if buy else -1, 2.0),
                    ("exit", "SL_TP1", "ECV", ("qty", 1.0), None, None, None, None, None, p["t1"], p["sl"]),
                    ("exit", "SL_TP2", "ECV", ("qty", 1.0), None, None, None, None, None, p["t2"], p["sl"])]
        if pos != 0 and S["st"] == "IN":
            with np.errstate(invalid="ignore"):
                if S["buy"] and c[i] >= S["be"] and not S["hit"]:
                    S["hit"] = True
                    out.append(("exit", "BE", "ECV", ("qty", 1.0), None, None, None, None, None, None, 0))
                if (not S["buy"]) and c[i] <= S["be"] and not S["hit"]:
                    S["hit"] = True
                    out.append(("exit", "BE", "ECV", ("qty", 1.0), None, None, None, None, None, None, 0))
        if pos == 0 and S["st"] == "IN":
            S.update(st="IDLE", be=np.nan, hit=False)
        return out

    ref = simulate_brackets(o, h, l, c, orders, tick=tick)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(cd=15, t1=100, t2=200, sl=50)


def check():
    df = bars(60000, seed=641, freq="5min")
    base = df["close"].iloc[0]
    for k in ("open", "high", "low", "close"):
        df[k] = 2000 * (df[k] / base) ** 0.04
    msgs, allok = [], True
    cases = (({"Cooldown Bars": 3, "TP1 (Ticks)": 40, "TP2 (Ticks)": 80, "Stop Loss (Ticks)": 20}, dict(cd=3, t1=40, t2=80, sl=20)),
             ({"Cooldown Bars": 5, "TP1 (Ticks)": 150, "TP2 (Ticks)": 300, "Stop Loss (Ticks)": 60}, dict(cd=5, t1=150, t2=300, sl=60)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
