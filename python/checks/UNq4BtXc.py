"""Independent check — GC Asia Session Breakout (UNq4BtXc): 15-minute bars (24 h synthetic, price ~100) of a stock-style symbol (New York time, trading day from 09:30), process_orders_on_close (orders fill at the signal close), default quantity 1, commission / slippage / margin off.
The Asia range (high / low of the bars with open time 18:00 - 24:00 NY) is cleared at each daily-period change (09:30); in the 00:00 - 03:00 window, with the one-trade-per-day flag clear, a close crossing over the range high (under the range low) with the EMA filter on the right side enters; ATR stop / target brackets (or fixed dollars) are re-issued every bar from the average entry price (none while flat);
when the trade window has just ended, any open position is closed at that bar's close. Uses the quantity-aware bracket reference (indep.simulate_brackets, on_close), comparing quantities too. Variants: defaults; EMA filter off and one-trade limit off; fixed $0.3 / $0.6 stop / target."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_cross_over, np_cross_under, np_ema, np_periods, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "UNq4BtXc"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    asia, trade = mins >= 1080, mins < 180
    pid, _ = np_periods(df, 1440)
    ema, atr = np_ema(c, 100), np_atr(h, l, c, 14)
    S = dict(hi=np.nan, lo=np.nan, td=False, prev=False)

    def orders(i, info):
        out = []
        pos, avg = info["pos"], info["avg"]
        nd = i > 0 and pid[i] != pid[i - 1]
        if nd:
            S["hi"] = S["lo"] = np.nan
        if asia[i]:
            S["hi"] = h[i] if np.isnan(S["hi"]) else max(S["hi"], h[i])
            S["lo"] = l[i] if np.isnan(S["lo"]) else min(S["lo"], l[i])
        if nd:
            S["td"] = False
        with np.errstate(invalid="ignore"):
            ready = not np.isnan(S["hi"]) and not np.isnan(S["lo"]) and S["hi"] > S["lo"]
            can = (not p["one"]) or not S["td"]
            xu = i > 0 and c[i] > S["hi"] and c[i - 1] <= prev_hi[0]
            xd = i > 0 and c[i] < S["lo"] and c[i - 1] >= prev_lo[0]
            lb = ready and trade[i] and can and ((not p["ema"]) or c[i] > ema[i]) and xu
            sb = ready and trade[i] and can and ((not p["ema"]) or c[i] < ema[i]) and xd
        prev_hi[0], prev_lo[0] = S["hi"], S["lo"]
        sd = p["fs"] if p["fixed"] else atr[i] * 1.2
        td_ = p["ft"] if p["fixed"] else atr[i] * 2.0
        if lb:
            out.append(("entry", "L", 1, 1.0))
            S["td"] = True
        if sb:
            out.append(("entry", "S", -1, 1.0))
            S["td"] = True
        if pos != 0 and not np.isnan(avg):
            out += [("exit", "L-Exit", "L", None, avg - sd, avg + td_), ("exit", "S-Exit", "S", None, avg + sd, avg - td_)]
        ending = (not trade[i]) and S["prev"]
        S["prev"] = bool(trade[i])
        if ending:
            out += [("close", "L"), ("close", "S")]
        return out

    prev_hi, prev_lo = [np.nan], [np.nan]
    ref = simulate_brackets(o, h, l, c, orders, on_close=True)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(one=True, ema=True, fixed=False, fs=4.0, ft=8.0)


def check():
    df = bars(60000, seed=481, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Use EMA Trend Filter": False, "Max 1 trade per day": False}, dict(ema=False, one=False)),
             ({"Use fixed $ stop/target (overrides ATR if ON)": True, "Stop ($)": 0.3, "Target ($)": 0.6}, dict(fixed=True, fs=0.3, ft=0.6)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
