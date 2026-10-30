"""Independent check — MES ORB v6 (oPHhrxiZ): 5-minute bars on an ES-type future (point value 5? the quantity does not change the trade list), market entries at the next open, one position. The 09:45-10:00 ET bars give the day's range (reset when the ET day of the month changes). From 10:00 on, a bar that CLOSES on a 15-minute boundary (minute of the close time divisible by 15) with close above range high + 2 points (below range low - 2), a bullish (bearish) 15-minute body (close vs the open 2 bars back) of at least 1 point, on an allowed weekday (Sun, Mon, Wed, Thu, Fri), at most one trade a day, ATR / retest filters if enabled, and not on the day after 2 consecutive losing trades (profit <= 0) - the skip applies to the next tradeable day - enters at the next open with stop 36 ticks / target 13 ticks (0.25) from the fill price, working from the fill bar. From 16:55 ET any open position is closed at the next open. Commission / slippage off on the pinelib side.
Variants: defaults; 2 trades a day with a retest requirement; ATR filter (2 - 25 points) with no loss-skip, Tuesdays allowed."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "oPHhrxiZ"


def one(df, params, days, max_td, retest, atr_f, skip_f, sl, tp):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    dom = ny.dt.day.to_numpy()
    dow = ((ny.dt.dayofweek.to_numpy() + 1) % 7) + 1     # Pine: Sunday = 1
    atr = np_atr(h, l, c, 15)
    log = []
    S = dict(oh=np.nan, ol=np.nan, td=0, cl=0, skip_next=False, skip_today=False, lc=0, wl=False, ws=False, rld=False, rsd=False, rsb=-1)

    def orders(i, pos):
        out = []
        newday = i > 0 and dom[i] != dom[i - 1]
        dayok = dow[i] in days
        if newday:
            S.update(oh=np.nan, ol=np.nan, td=0)
        if 585 <= m[i] < 600:
            S["oh"] = h[i] if np.isnan(S["oh"]) else max(S["oh"], h[i])
            S["ol"] = l[i] if np.isnan(S["ol"]) else min(S["ol"], l[i])
        is15 = int(np.floor(((m[i] % 60) + 5) + 0.5)) % 15 == 0
        o15 = o[i - 2] if i >= 2 else np.nan
        body = abs(c[i] - o15)
        if newday:
            if dayok:
                S["skip_today"] = S["skip_next"]
                S["skip_next"] = False
            else:
                S["skip_today"] = False
        if len(log) > S["lc"]:
            for t in log[S["lc"]:]:
                pnl = t[0] * (t[4] - t[2])
                if pnl <= 0:
                    S["cl"] += 1
                    if S["cl"] >= 2:
                        S["skip_next"] = True
                        S["cl"] = 0
                else:
                    S["cl"] = 0
            S["lc"] = len(log)
        skip = skip_f and S["skip_today"]
        if newday:
            S.update(wl=False, ws=False, rld=False, rsd=False, rsb=-1)
        done = m[i] >= 600
        with np.errstate(invalid="ignore"):
            ibl = done and is15 and c[i] > S["oh"] + 2.0
            ibs = done and is15 and c[i] < S["ol"] - 2.0
        if retest and ibl and not S["wl"] and not S["rld"]:
            S["wl"], S["rsb"] = True, i
        if retest and ibs and not S["ws"] and not S["rsd"]:
            S["ws"], S["rsb"] = True, i
        if S["wl"] and l[i] <= S["oh"] + 0.25:
            S["rld"], S["wl"] = True, False
        if S["ws"] and h[i] >= S["ol"] - 0.25:
            S["rsd"], S["ws"] = True, False
        if S["wl"] and S["rsb"] >= 0 and i - S["rsb"] > 4:
            S["wl"] = False
        if S["ws"] and S["rsb"] >= 0 and i - S["rsb"] > 4:
            S["ws"] = False
        rlok = (not retest) or S["rld"]
        rsok = (not retest) or S["rsd"]
        atrok = (not atr_f) or (not np.isnan(atr[i]) and 2.0 <= atr[i] <= 25.0)
        traded = S["td"] >= max_td
        with np.errstate(invalid="ignore"):
            bl = ibl and c[i] > o15 and body >= 1.0 and not traded and dayok and atrok and rlok and not skip
            bs = ibs and c[i] < o15 and body >= 1.0 and not traded and dayok and atrok and rsok and not skip
        if bl and pos == 0:
            S["td"] += 1
            out.append(("entry", 1))
        if bs and pos == 0:
            S["td"] += 1
            out.append(("entry", -1))
        if (m[i] >= 16 * 60 + 55) and pos != 0:
            out.append(("close", pos))
        return out

    stop = lambda i, pos, ep, eb: ep - pos * sl * 0.25
    tgt = lambda i, pos, ep, eb: ep + pos * tp * 0.25
    ref = simulate(o, h, l, c, orders, stop=stop, target=tgt, log=log)
    sym = SymbolInfo.make("CME_MINI:MES1!", "futures", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides={"commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(40000, seed=88, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 5000 * (df[k] / 100) ** 0.06
    msgs, allok = [], True
    base_days = {1, 2, 4, 5, 6}
    cases = (({}, (base_days, 1, False, False, True, 36, 13)),
             ({"Max trades/día": 2, "Retest entry": True}, (base_days, 2, True, False, True, 36, 13)),
             ({"Filtro ATR": True, "Skip día post-N losses": False, "Martes": True, "SL (ticks)": 20, "TP (ticks)": 20}, (base_days | {3}, 1, False, True, False, 20, 20)))
    for params, args in cases:
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
