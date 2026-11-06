"""Independent check — ATR Momentum Rider (jd1KSVn7): 4000 daily business-day bars (price ~100, stamped 09:30 New York) of a stock-style symbol, one contract per entry, pyramiding 2, market orders at the next open, commission / slippage off.
Triple-HMA regime start (8 / 9 / 20, floor half-length and rounded root length), the ATR-scaled 3-bar slope gate, the year window, the two alternating entry ids with close-then-entry renewal, the entry record on the bar after the order, the peak / trailing K1 state (ATR activation, percent trail, wait sessions) and the end-year close are restated bar by bar.
Uses the quantity-aware bracket reference (indep.simulate_brackets). Variants: defaults with start year 2015; a 3-ATR-less trail (activation 0.5 ATR, trail 2 %, wait 1) with end year 2019."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_wma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "jd1KSVn7"


def hma(x, n):
    return np_wma(2.0 * np_wma(x, max(1, int(np.floor(n / 2.0)))) - np_wma(x, n), max(1, int(np.floor(np.sqrt(n) + 0.5))))


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    year = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York").dt.year.to_numpy()
    hf, hm, hs = hma(c, 8), hma(c, 9), hma(c, 20)
    atr = np_atr(h, l, c, 14)
    S = dict(act_id="L-A", reset=False, rbar=None, patr=np.nan, ep=np.nan, ea=np.nan, peak=np.nan, trail=np.nan, kact=False, ebar=None, prev_regime=None)

    def orders(i, info):
        out = []
        pos, avg = info["pos"], info["avg"]
        with np.errstate(invalid="ignore"):
            regime = bool(hf[i] > hm[i] and hm[i] > hs[i])
            raw = regime and not (S["prev_regime"] is True)
            slope = (hs[i] - hs[i - 3]) / 3 / atr[i] if (i >= 3 and atr[i] > 0) else np.nan
            setup = raw and (not np.isnan(slope)) and slope >= -0.18
        S["prev_regime"] = regime
        in_range = p["y0"] <= year[i] <= p["y1"]
        if S["reset"] and S["rbar"] is not None and i > S["rbar"] and pos > 0:
            S["ep"], S["ea"], S["peak"], S["trail"], S["kact"], S["ebar"], S["reset"] = avg, S["patr"], h[i], np.nan, False, i, False
        if pos == 0 and not S["reset"]:
            S["ep"] = S["ea"] = S["peak"] = S["trail"] = np.nan
            S["kact"], S["ebar"] = False, None
        kx = False
        if pos > 0 and not S["reset"]:
            S["peak"] = max(h[i] if np.isnan(S["peak"]) else S["peak"], h[i])
            if S["kact"]:
                cand = S["peak"] * (1.0 - p["trail"] / 100.0)
                S["trail"] = max(cand if np.isnan(S["trail"]) else S["trail"], cand)
                kx = i >= S["ebar"] + p["wait"] and c[i] <= S["trail"]
            mfe = (S["peak"] - S["ep"]) / S["ea"] if S["ea"] > 0 else np.nan
            if (not S["kact"]) and (not np.isnan(mfe)) and mfe >= p["act"]:
                S["kact"], S["trail"] = True, np.nan
        if in_range and setup and not np.isnan(atr[i]):
            if pos > 0:
                nid = "L-B" if S["act_id"] == "L-A" else "L-A"
                out += [("close", S["act_id"]), ("entry", nid, 1, 1.0)]
                S["act_id"] = nid
            else:
                out.append(("entry", S["act_id"], 1, 1.0))
            S["patr"], S["rbar"], S["reset"] = atr[i], i, True
        elif kx:
            out.append(("close", S["act_id"]))
        if year[i] > p["y1"] and pos > 0:
            out.append(("close", S["act_id"]))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=2, tick=0.01, qty_step=1e-9)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params,
                                     strategy_overrides={"margin_long": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


def check():
    df = bars(4000, seed=5, freq="B")
    df["time"] = df["time"] + int(14.5 * 3600 * 1000)
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.6
    msgs, allok = [], True
    cases = (({"Start year": 2015}, dict(y0=2015, y1=2099, act=1.5, trail=5.75, wait=4)),
             ({"Start year": 2015, "End year": 2019, "K1-A · ATR activation": 0.5, "K1-T · Peak trail (%)": 2.0, "K1-W · Wait sessions": 1}, dict(y0=2015, y1=2019, act=0.5, trail=2.0, wait=1)))
    for params, ov in cases:
        ok, m = one(df, params, ov)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
