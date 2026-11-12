"""Independent check — Refined Supertrend ATR + TSL (c1XpwWU4): 15-minute bars (24 h synthetic, price ~100) of a stock-style symbol, market orders at the next open, fixed quantity 10 on the pinelib side (the original sizes 10 % of equity), commission / slippage / margin off.
Entry: close crossing over / under the Supertrend line with EMA200 side, ADX > threshold and the Kolkata session (bar open time 09:15 - 15:30 Asia/Kolkata); reversals. The script's trailing-stop tracker is restated (max of nz(prev) and close - ATR x mult for longs, min(nz(prev), ...) for shorts - which sticks at 0 - and the break-even raise); every bar of a position re-issues take-profit orders of 40 / 30 / 30 % at R multiples of the ATR from the average entry
plus the stop order at max(Supertrend line, tracker) (min for shorts). Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too. Variants: defaults with ADX 10; session filter off with factor 2 and TP multiples 1 / 2 / 3."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_cross_over, np_cross_under, np_dmi, np_ema, np_supertrend, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "c1XpwWU4"
QTY = 10.0


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ist = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Asia/Kolkata")
    mins = (ist.dt.hour * 60 + ist.dt.minute).to_numpy()
    sess = (mins >= 555) & (mins < 930) if p["us"] else np.ones(n, bool)
    atr = np_atr(h, l, c, 10)
    line, _ = np_supertrend(h, l, c, p["f"], 10)
    ema = np_ema(c, 200)
    _, _, adx = np_dmi(h, l, c, 14)
    xu, xd = np_cross_over(c, line), np_cross_under(c, line)
    S = dict(ltsl=np.nan, stsl=np.nan)
    nz = lambda x: 0.0 if np.isnan(x) else x

    def orders(i, info):
        out = []
        pos, avg = info["pos"], info["avg"]
        with np.errstate(invalid="ignore"):
            strong = adx[i] > p["adx"]
            lc = bool(xu[i]) and c[i] > ema[i] and strong and sess[i]
            sc = bool(xd[i]) and c[i] < ema[i] and strong and sess[i]
        if lc:
            out.append(("entry", "Long", 1, QTY))
        if sc:
            out.append(("entry", "Short", -1, QTY))
        ep = avg if pos != 0 else np.nan
        if pos == 0:
            S["ltsl"] = S["stsl"] = np.nan
        if pos > 0:
            S["ltsl"] = max(nz(S["ltsl"]), c[i] - 2.0 * atr[i])
        if pos < 0:
            S["stsl"] = min(nz(S["stsl"]), c[i] + 2.0 * atr[i])
        if pos > 0 and c[i] >= ep + 1.5 * atr[i]:
            S["ltsl"] = max(nz(S["ltsl"]), ep)
        if pos < 0 and c[i] <= ep - 1.5 * atr[i]:
            S["stsl"] = min(nz(S["stsl"]), ep)
        m1, m2, m3 = p["tp"]
        if pos > 0:
            out += [("exit", "TP1 Long", "Long", 40, None, ep + m1 * atr[i]), ("exit", "TP2 Long", "Long", 30, None, ep + m2 * atr[i]),
                    ("exit", "TP3 Long", "Long", 30, None, ep + m3 * atr[i]), ("exit", "TSL Long", "Long", None, max(line[i], nz(S["ltsl"])), None)]
        if pos < 0:
            out += [("exit", "TP1 Short", "Short", 40, None, ep - m1 * atr[i]), ("exit", "TP2 Short", "Short", 30, None, ep - m2 * atr[i]),
                    ("exit", "TP3 Short", "Short", 30, None, ep - m3 * atr[i]), ("exit", "TSL Short", "Short", None, min(line[i], nz(S["stsl"])), None)]
        return out

    ref = simulate_brackets(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(adx=20, us=True, f=3.0, tp=(1.5, 3.0, 5.0))


def check():
    df = bars(60000, seed=511, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    cases = (({"ADX Minimum Threshold": 10}, dict(adx=10)),
             ({"Use Indian Market Session (9:15-15:30)": False, "Supertrend Factor": 2.0, "TP1 (R) - Close 40%": 1.0, "TP2 (R) - Close 30%": 2.0, "TP3 (R) - Close 30%": 3.0},
              dict(us=False, f=2.0, tp=(1.0, 2.0, 3.0))))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
