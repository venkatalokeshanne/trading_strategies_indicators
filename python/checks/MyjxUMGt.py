"""Independent check — Initial Balance Breakout (MyjxUMGt): 5-minute bars (24 h synthetic, compressed), process_orders_on_close for the time-stop close only, resting limit entries. The 09:30-10:30 ET bars form the initial balance (reset at 09:30, locked on the 10:30 bar); valid when its size is 0.3-1.5 % of its high. In the entry window (10:30-13:00) the flags broke_high / broke_low are set by a bar's high above / low below the IB. When exactly one side has broken (and nothing placed or traded today) a limit entry is placed at the retracement (25 % of the IB range back from the broken side: IB high - 0.25 x range for longs, IB low + 0.25 x range for shorts) with its exit (stop = IB high - 60 % of the range, target = IB high + 0.5 x range; mirrored) attached; the pending order is cancelled (with everything) when outside the window or when the opposite side breaks while nothing is filled; from 15:30 any open position is closed at the bar close. Uses the pending-order reference broker (simulate_ord, on_close). Commission / slippage / margin off on the pinelib side.
Variants: defaults; retracement 40 % with a 1.0 target multiple and a 14:00 window end."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion, simulate_ord

TV_ID = "MyjxUMGt"


def one(df, params, retr, tpm, wend):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    S = dict(ih=np.nan, il=np.nan, ir=np.nan, valid=False, locked=False, traded=False, bh=False, bl=False, placed=False, dir=0)

    def orders(i, pos):
        out = []
        if m[i] == 570:
            S.update(ih=h[i], il=l[i], locked=False, valid=False, traded=False, bh=False, bl=False, placed=False)
        if 570 <= m[i] < 630 and not S["locked"]:
            S["ih"], S["il"] = max(S["ih"], h[i]), min(S["il"], l[i])
        if m[i] == 630 and not S["locked"] and not np.isnan(S["ih"]):
            S["locked"] = True
            S["ir"] = S["ih"] - S["il"]
            pct = S["ir"] / S["ih"] * 100 if S["ih"] > 0 else 0.0
            S["valid"] = 0.3 <= pct <= 1.5
        inw = 630 <= m[i] < wend
        if S["locked"] and S["valid"] and inw and not S["traded"]:
            if h[i] > S["ih"]:
                S["bh"] = True
            if l[i] < S["il"]:
                S["bl"] = True
        if pos != 0 and not S["traded"]:
            S["traded"] = True
        base = S["locked"] and S["valid"] and inw and not S["traded"] and not S["placed"]
        lo_ = base and S["bh"] and not S["bl"]
        so_ = base and S["bl"] and not S["bh"]
        ih, il, ir = S["ih"], S["il"], S["ir"]
        if lo_ and pos == 0:
            S.update(placed=True, dir=1)
            out += [("entry", "Long", 1, None, ih - ir * retr / 100), ("exit", "Long TP", "Long", ih - ir * 0.6, ih + ir * tpm)]
        elif so_ and pos == 0:
            S.update(placed=True, dir=-1)
            out += [("entry", "Short", -1, None, il + ir * retr / 100), ("exit", "Short TP", "Short", il + ir * 0.6, il - ir * tpm)]
        if S["placed"] and not S["traded"] and pos == 0:
            if (not inw) or (S["dir"] == 1 and S["bl"]) or (S["dir"] == -1 and S["bh"]):
                out.append(("cancel_all",))
                S["placed"] = False
        if m[i] >= 930 and pos != 0:
            out.append(("close_all",))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate_ord(o, h, l, c, orders, on_close=True)
    from pinelib import SymbolInfo
    sym = SymbolInfo.make("CME_MINI:ES1!", "futures", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides={"slippage": 0, "commission_value": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    from pinelib import SymbolInfo
    df = bars(40000, seed=616, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 5000 * (df[k] / 100) ** 0.1
    msgs, allok = [], True
    for params, args in (({}, (25.0, 0.5, 780)), ({"Retracement % for Entry": 40.0, "TP Multiplier (× IB)": 1.0, "Entry Window End Hour": 14}, (40.0, 1.0, 840))):
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
