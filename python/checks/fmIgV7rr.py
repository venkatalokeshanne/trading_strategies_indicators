"""Independent check — MSG Ultimate v5.1 (fmIgV7rr): 15-minute bars (24 h synthetic, price ~100) of a stock-style symbol (New York time), market orders at the next open, fixed quantity 10 on the pinelib side, pyramiding 0, commission / slippage / margin off.
Session means = midpoint of each session's first bar (Asia 00:00 - 06:00, London 07:00 - 12:00, NY 13:00 - 17:00 bar open times). Previous mean = NY else London else Asia (latest recorded); current mean by the session the bar is in (Asia's when in none). Bull: close above both means + 0.5 ATR and above EMA50 (bear mirrored); probability = 30 + 35 per true flag (capped 100, minimum 50 -> a flag is needed);
buy / sell also need bias (close vs the current mean) and an enabled session; one trade per session start. Every bar an exit order per side around the close (ATR x mult, limit and stop). Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too. Variants: defaults; Asia enabled with a 1.0 multiplier; London only with EMA 20."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_ema, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "fmIgV7rr"
QTY = 10.0


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    asia, lon, nyy = mins < 360, (mins >= 420) & (mins < 720), (mins >= 780) & (mins < 1020)
    ema, atr = np_ema(c, p["ema"]), np_atr(h, l, c, 14)
    S = dict(am=np.nan, lm=np.nan, nm=np.nan, tr=False, pa=False, pl=False, pn=False)

    def orders(i, info):
        out = []
        a0, l0, n0 = asia[i] and not S["pa"], lon[i] and not S["pl"], nyy[i] and not S["pn"]
        S.update(pa=bool(asia[i]), pl=bool(lon[i]), pn=bool(nyy[i]))
        valid = (asia[i] and p["ta"]) or (lon[i] and p["tl"]) or (nyy[i] and p["tn"])
        buf = atr[i] * 0.5
        if a0:
            S["am"] = (h[i] + l[i]) / 2
        if l0:
            S["lm"] = (h[i] + l[i]) / 2
        if n0:
            S["nm"] = (h[i] + l[i]) / 2
        pm = S["nm"] if not np.isnan(S["nm"]) else (S["lm"] if not np.isnan(S["lm"]) else S["am"])
        cm = S["nm"] if nyy[i] else (S["lm"] if lon[i] else S["am"])
        with np.errstate(invalid="ignore"):
            bias = 1 if c[i] > cm else -1
            bull = c[i] > pm + buf and c[i] > cm + buf and c[i] > ema[i]
            bear = c[i] < pm - buf and c[i] < cm - buf and c[i] < ema[i]
        prob = min(100, 30 + (int(bull) + int(bear)) * 35)
        buy = bull and bias == 1 and prob >= 50 and valid
        sell = bear and bias == -1 and prob >= 50 and valid
        if a0 or l0 or n0:
            S["tr"] = False
        if buy and not S["tr"]:
            out.append(("entry", "BUY", 1, QTY))
            S["tr"] = True
        if sell and not S["tr"]:
            out.append(("entry", "SELL", -1, QTY))
            S["tr"] = True
        a, m = atr[i], p["m"]
        nn = lambda x: None if np.isnan(x) else x
        out += [("exit", "TP BUY", "BUY", None, nn(c[i] - a * m), nn(c[i] + a * m)), ("exit", "TP SELL", "SELL", None, nn(c[i] + a * m), nn(c[i] - a * m))]
        return out

    ref = simulate_brackets(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(ema=50, m=1.5, ta=False, tl=True, tn=True)


def check():
    df = bars(40000, seed=651, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    cases = (({}, {}), ({"Trade Asia": True, "TP/SL Multiplier": 1.0}, dict(ta=True, m=1.0)),
             ({"Trade New York": False, "EMA Length": 20}, dict(tn=False, ema=20)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
