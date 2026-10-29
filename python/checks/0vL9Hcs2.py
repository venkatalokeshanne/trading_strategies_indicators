"""Independent check — NY Open 3H Sweep (0vL9Hcs2): 15-minute bars (24h synthetic) on a stock chart (NY day from 09:30, 180-minute higher-timeframe blocks counted from 09:30), process_orders_on_close, one position. The previous 3-hour bar's high / low (security of high[1] / low[1], lookahead off) are the sweep levels. Inside 09:00-10:30 NY, flat, with a trade still allowed that day:
a bar below the previous-3H low arms a long and accumulates the lowest low; above the previous-3H high arms a short (highest high). The entry level is the latest confirmed pivot high (long) / low (short) with 2 bars each side; long stop = sweep low - 2 ticks, target = previous-3H high (short mirrored); a setup is ready when stop < level < target (long). A bar whose high reaches the level (low for shorts)
enters at the close (long first, then short if it triggers too: the second one reverses). After the fill the stop moves to the entry price once the high reaches entry + 1R (risk = entry - stop); the stop / target are issued from the first script run that sees the position (works from the next bar). Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_periods, np_security_lookahead_off, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "0vL9Hcs2"
K = 2


def one(df, params, s0, s1, one_trade):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    pid, last_of = np_periods(df, 180)
    npd = pid[-1] + 1
    ph3 = np.array([h[pid == p].max() for p in range(npd)])
    pl3 = np.array([l[pid == p].min() for p in range(npd)])
    sh1 = lambda x: np.r_[np.nan, x[:-1]]
    h3h = np_security_lookahead_off(sh1(ph3), pid, last_of)
    h3l = np_security_lookahead_off(sh1(pl3), pid, last_of)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    day = (ny.dt.tz_localize(None) - pd.Timedelta(minutes=9 * 60 + 30)).dt.date.to_numpy()
    sess = (m >= s0) & (m < s1)
    piv_h, piv_l = np.full(n, np.nan), np.full(n, np.nan)
    for i in range(2 * K, n):
        j = i - K
        if h[j] > h[j - K:j].max() and h[j] > h[j + 1:i + 1].max():
            piv_h[i] = h[j]
        if l[j] < l[j - K:j].min() and l[j] < l[j + 1:i + 1].min():
            piv_l[i] = l[j]
    S = dict(traded=False, lsh=np.nan, lsl=np.nan, lsd=False, ssd=False, lsw=np.nan, ssw=np.nan, lel=np.nan, sel=np.nan, lsl_=np.nan, ltp=np.nan, ssl_=np.nan, stp=np.nan,
             aLs=np.nan, aLt=np.nan, aSs=np.nan, aSt=np.nan, lbe=False, sbe=False, ep=np.nan)
    poscl = np.zeros(n)
    sl_arr, tp_arr = np.full(n, np.nan), np.full(n, np.nan)
    buf = 2 * 0.01
    nan = np.nan

    def orders(i, pos):
        poscl[i] = pos
        out = []
        prev = poscl[i - 1] if i else nan
        new_day = i > 0 and day[i] != day[i - 1]
        if new_day:
            S["traded"] = False
        can = (not S["traded"]) if one_trade else True
        if not np.isnan(piv_h[i]):
            S["lsh"] = piv_h[i]
        if not np.isnan(piv_l[i]):
            S["lsl"] = piv_l[i]
        if new_day:
            S.update(lsd=False, ssd=False, lsw=nan, ssw=nan, lel=nan, sel=nan, lsl_=nan, ltp=nan, ssl_=nan, stp=nan)
        if sess[i] and can and pos == 0:
            if l[i] < h3l[i]:
                S["lsd"] = True
                S["lsw"] = l[i] if np.isnan(S["lsw"]) else min(S["lsw"], l[i])
            if h[i] > h3h[i]:
                S["ssd"] = True
                S["ssw"] = h[i] if np.isnan(S["ssw"]) else max(S["ssw"], h[i])
        if sess[i] and can and pos == 0:
            if S["lsd"] and not np.isnan(S["lsh"]):
                S["lel"], S["lsl_"], S["ltp"] = S["lsh"], S["lsw"] - buf, h3h[i]
            if S["ssd"] and not np.isnan(S["lsl"]):
                S["sel"], S["ssl_"], S["stp"] = S["lsl"], S["ssw"] + buf, h3l[i]
        with np.errstate(invalid="ignore"):
            lr = sess[i] and can and pos == 0 and S["lsd"] and S["lel"] > S["lsl_"] and S["ltp"] > S["lel"]
            sr = sess[i] and can and pos == 0 and S["ssd"] and S["sel"] < S["ssl_"] and S["stp"] < S["sel"]
            lt = lr and h[i] >= S["lel"]
            st = sr and l[i] <= S["sel"]
        if lt:
            out.append(("entry", 1))
            S["traded"] = True
        if st:
            out.append(("entry", -1))
            S["traded"] = True
        if pos > 0 and prev <= 0:
            S["aLs"], S["aLt"], S["lbe"] = S["lsl_"], S["ltp"], False
        if pos < 0 and prev >= 0:
            S["aSs"], S["aSt"], S["sbe"] = S["ssl_"], S["stp"], False
        if pos == 0:
            S.update(aLs=nan, aLt=nan, aSs=nan, aSt=nan, lbe=False, sbe=False)
        if pos > 0 and not S["lbe"] and not np.isnan(S["aLs"]):
            risk = S["ep"] - S["aLs"]
            if risk > 0 and h[i] >= S["ep"] + risk:
                S["aLs"], S["lbe"] = S["ep"], True
        if pos < 0 and not S["sbe"] and not np.isnan(S["aSs"]):
            risk = S["aSs"] - S["ep"]
            if risk > 0 and l[i] <= S["ep"] - risk:
                S["aSs"], S["sbe"] = S["ep"], True
        if pos > 0:
            sl_arr[i], tp_arr[i] = S["aLs"], S["aLt"]
        if pos < 0:
            sl_arr[i], tp_arr[i] = S["aSs"], S["aSt"]
        return out

    def lvl(arr):
        def f(i, pos, ep, eb):
            S["ep"] = ep
            return None if (i == 0 or eb >= i or poscl[i - 1] * pos <= 0 or np.isnan(arr[i - 1])) else arr[i - 1]
        return f

    sf, tf = lvl(sl_arr), lvl(tp_arr)

    def stop(i, pos, ep, eb):
        S["ep"] = ep
        return sf(i, pos, ep, eb)

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tf, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok, d, len(ref)


def check():
    df = bars(100000, seed=881, freq="15min")
    msgs, allok, tot = [], True, 0
    for params, s0, s1, ot in (({}, 540, 630, True), ({"NY Trading Window": "0900-1600", "Max 1 Trade Per Day": False}, 540, 960, False)):
        ok, d, k = one(df, params, s0, s1, ot)
        allok &= ok
        tot += k
        msgs.append(f"{d} (got {k})")
    return allok and tot > 10, " | ".join(msgs)
