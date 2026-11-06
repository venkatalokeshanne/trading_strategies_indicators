"""Independent check — GEMINI QUANT PRO (uSO9nAI2): 15-minute bars (24 h synthetic, price ~100) of a stock-style symbol (daily periods from 09:30 New York, 4-hour periods from 09:30), market orders at the next open, fixed quantity 10 on the pinelib side, commission / slippage / margin off.
Trend of a higher timeframe = +1 if its (period) close is above its EMA(200) of period closes, otherwise -1 (so -1 while the EMA is not yet available); lookahead off (a period's value shows on its last chart bar, the previous period's before that). Entry: retest of the chart EMA(44) (low <= it, close back above it and above the chart EMA(200); mirrored for shorts) with volume over its 20-bar SMA and both daily and 4-hour trends in agreement;
the stop is the bar low / high with the buffer, the stored reward level 3 is the target; an exit order for each side with the stored (possibly na) levels is re-issued every bar. Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too.
Variants: defaults; buffer 0.5 % and RR3 = 2.5; EMA 44 -> 20 and EMA 200 -> 100 (the data span covers the daily EMA warm-up)."""
import numpy as np

from indep import bars, compare_q, np_ema, np_periods, np_security_lookahead_off, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "uSO9nAI2"
QTY = 10.0


def trend(df, c, minutes, e200):
    pid, last_of = np_periods(df, minutes)
    pc = c[last_of]
    hc = np_security_lookahead_off(pc, pid, last_of)
    he = np_security_lookahead_off(np_ema(pc, e200), pid, last_of)
    return np.where(hc > he, 1, -1)


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    t1d, t4h = trend(df, c, 1440, p["e200"]), trend(df, c, 240, p["e200"])
    e44, e200 = np_ema(c, p["e44"]), np_ema(c, p["e200"])
    va = np_sma(v, 20)
    S = dict(sl=np.nan, tp3=np.nan)

    def orders(i, info):
        out = []
        pos = info["pos"]
        with np.errstate(invalid="ignore"):
            br = l[i] <= e44[i] and c[i] > e44[i] and c[i] > e200[i]
            sr = h[i] >= e44[i] and c[i] < e44[i] and c[i] < e200[i]
            vf = v[i] > va[i]
            lc = br and t1d[i] == 1 and t4h[i] == 1 and vf
            sc = sr and t1d[i] == -1 and t4h[i] == -1 and vf
        if lc and pos == 0:
            sl = l[i] * (1 - p["buf"])
            risk = c[i] - sl
            S.update(sl=sl, tp3=c[i] + risk * p["rr3"])
            out.append(("entry", "Long", 1, QTY))
        if sc and pos == 0:
            sl = h[i] * (1 + p["buf"])
            risk = sl - c[i]
            S.update(sl=sl, tp3=c[i] - risk * p["rr3"])
            out.append(("entry", "Short", -1, QTY))
        sl_ = None if np.isnan(S["sl"]) else S["sl"]
        tp_ = None if np.isnan(S["tp3"]) else S["tp3"]
        out += [("exit", "TP/SL Long", "Long", None, sl_, tp_), ("exit", "TP/SL Short", "Short", None, sl_, tp_)]
        return out

    ref = simulate_brackets(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(e44=44, e200=200, buf=0.002, rr3=5.0)


def check():
    df = bars(80000, seed=411, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    cases = (({}, {}), ({"SL Buffer (%)": 0.5, "TP3 Profit Ratio (RR)": 2.5}, dict(buf=0.005, rr3=2.5)),
             ({"EMA 44 Length": 20, "EMA 200 Length": 100}, dict(e44=20, e200=100)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
