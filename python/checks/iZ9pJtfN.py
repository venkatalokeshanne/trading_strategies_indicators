"""Independent check — MNQ Midpoint Retest (iZ9pJtfN): 5-minute bars (24 h synthetic, price ~15000, 0.25 tick) of a CME futures symbol (trading days from 17:00 Chicago), market orders at the next open, 10 units, pyramiding 10, commission / slippage / margin off.
The 08:00 - 08:15 New York range is built and locked each trading day (everything is cleared at the daily-period change); a close beyond the range sets the breakout state (never cleared); in 09:45 - 11:00 with the range locked, a retest of the midpoint (low <= mid after an upside break / high >= mid after a downside break) with no open trade enters 10 units.
Every bar re-issues, per side, an exit order for 70 % (limit 2R from the entry, stop at the range edge) and one for 30 % (limit 4R, stop at the entry once the script's flag - set when the bar extreme reached 2R - is on); the 'entry' price is read from the position average when a position first exists, risks use the CURRENT range edge. A position is closed at the end of the trade window.
Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too. Variants: defaults on a long sample; the same data with a different seed."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_periods, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "iZ9pJtfN"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    rng_s = (mins >= 480) & (mins < 495)
    trd_s = (mins >= 585) & (mins < 660)
    pid, _ = np_periods(df, 1440, start_minutes=17 * 60, tz="America/Chicago")
    S = dict(rh=np.nan, rl=np.nan, mid=np.nan, locked=False, entry=np.nan, l1=False, s1=False, bs=0, prev=0.0)

    def orders(i, info):
        out = []
        pos = info["pos"]
        if i > 0 and pid[i] != pid[i - 1]:
            S.update(rh=np.nan, rl=np.nan, mid=np.nan, locked=False, entry=np.nan, l1=False, s1=False)
        if rng_s[i] and not S["locked"]:
            S["rh"] = h[i] if np.isnan(S["rh"]) else max(S["rh"], h[i])
            S["rl"] = l[i] if np.isnan(S["rl"]) else min(S["rl"], l[i])
        if (not rng_s[i]) and not S["locked"] and not np.isnan(S["rh"]) and not np.isnan(S["rl"]):
            S["mid"] = (S["rh"] + S["rl"]) / 2
            S["locked"] = True
        end = i > 0 and (not trd_s[i]) and trd_s[i - 1]
        if end and pos != 0:
            out.append(("close_all",))
        with np.errstate(invalid="ignore"):
            if S["locked"] and c[i] > S["rh"]:
                S["bs"] = 1
            if S["locked"] and c[i] < S["rl"]:
                S["bs"] = -1
            can = S["locked"] and trd_s[i]
            tl = can and S["bs"] == 1 and l[i] <= S["mid"]
            ts = can and S["bs"] == -1 and h[i] >= S["mid"]
        if tl and info["n"] == 0:
            out.append(("entry", "LONG", 1, 10.0))
        if ts and info["n"] == 0:
            out.append(("entry", "SHORT", -1, 10.0))
        if pos != 0 and S["prev"] == 0:
            S.update(entry=info["avg"], l1=False, s1=False)
        lst, sst = S["rl"], S["rh"]
        e = S["entry"]
        with np.errstate(invalid="ignore"):
            lr = np.nan if np.isnan(e) else e - lst
            sr = np.nan if np.isnan(e) else sst - e
            lt1, lt2 = e + 2 * lr, e + 4 * lr
            st1, st2 = e - 2 * sr, e - 4 * sr
            if pos > 0 and not S["l1"] and h[i] >= lt1:
                S["l1"] = True
            if pos < 0 and not S["s1"] and l[i] <= st1:
                S["s1"] = True
        nn = lambda x: None if np.isnan(x) else x
        bl = e if S["l1"] else lst
        bsl = e if S["s1"] else sst
        out += [("exit", "L_TP1", "LONG", 70, nn(lst), nn(lt1)), ("exit", "S_TP1", "SHORT", 70, nn(sst), nn(st1)),
                ("exit", "L_RUN", "LONG", 30, nn(bl), nn(lt2)), ("exit", "S_RUN", "SHORT", 30, nn(bsl), nn(st2))]
        S["prev"] = pos
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=10, tick=0.25)
    sym = SymbolInfo.make("CME_MINI:MNQ1!", "futures", mintick=0.25, qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


def check():
    msgs, allok = [], True
    for seed in (501, 502):
        df = bars(60000, seed=seed, freq="5min")
        base = df["close"].iloc[0]
        for k in ("open", "high", "low", "close"):
            df[k] = 15000 * (df[k] / base) ** 0.05
        ok, m = one(df, {}, {})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
