"""Independent check — Elite Hybrid ORB (SPvazS2g): 5-minute bars (24h synthetic), New York clock, one position, market entries / closes at the next open. Session 09:30-13:00 (Asia preset 19:00-23:00): the first 30 minutes' high / low (reset at the first bar of each session) form the range, ready from the first bar at or after 10:00; valid when 2 <= width / tick <= 4000.
Trading window 10:00 up to 15 minutes before the session end; flat only; at most 4 entries per session. Long: close above range high + 5 % of the width (short: below low - 5 %); stop = opposite range side, target = close +/- width x TP multiple, placed with the entry (work from the fill bar). Bars starting in the 5 minutes at flat-at (12:45) close any position at the next open.
Variants: default; Asia preset with a 1.5x target; long only. Slippage / commission / margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "SPvazS2g"


def one(df, params, s0, s1, tpm, long_only):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    orb_end, flat_at = s0 + 30, s1 - 15
    in_s = (m >= s0) & (m < s1)
    in_o = (m >= s0) & (m < orb_end)
    trading = (m >= orb_end) & (m < flat_at)
    flatten = (m >= flat_at) & (m < flat_at + 5)
    S = dict(oh=np.nan, ol=np.nan, ready=False, tc=0, was=False)
    lev = {}

    def orders(i, pos):
        out = []
        new_s = in_s[i] and not S["was"]
        S["was"] = in_s[i]
        if new_s:
            S.update(oh=h[i], ol=l[i], ready=False, tc=0)
        if in_o[i] and not new_s:
            S["oh"], S["ol"] = max(S["oh"], h[i]), min(S["ol"], l[i])
        if in_s[i] and m[i] >= orb_end and not S["ready"] and not np.isnan(S["oh"]) and not np.isnan(S["ol"]):
            S["ready"] = True
        if S["ready"]:
            w = S["oh"] - S["ol"]
            ticks = w / 0.01
            valid = 2 <= ticks <= 4000
            buf = w * 0.05
            can = trading[i] and S["tc"] < 4 and pos == 0
            if can and valid and c[i] > S["oh"] + buf:
                out.append(("entry", 1))
                lev[i] = (S["ol"], c[i] + w * tpm)
                S["tc"] += 1
            elif can and valid and (not long_only) and c[i] < S["ol"] - buf:
                out.append(("entry", -1))
                lev[i] = (S["oh"], c[i] - w * tpm)
                S["tc"] += 1
        if flatten[i] and pos != 0:
            out.append(("close", pos))
        return out

    stop = lambda i, pos, ep, eb: lev[eb - 1][0] if eb - 1 in lev else None
    tgt = lambda i, pos, ep, eb: lev[eb - 1][1] if eb - 1 in lev else None
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "commission_value": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(50000, seed=831, freq="5min")
    msgs, allok = [], True
    for params, s0, s1, tpm, lo in (({}, 570, 780, 1.0, False),
                                    ({"Session preset": "Asia (Nikkei hours)", "TP multiplier (x ORB width)": 1.5}, 1140, 1380, 1.5, False),
                                    ({"Long only mode": True}, 570, 780, 1.0, True)):
        ok, m = one(df, params, s0, s1, tpm, lo)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
