"""Independent check — XAUUSD Elliott V17 H4 Filter (lv5jFTZN): 15-minute bars (price scaled into the 2000s) of a crypto-style symbol (4-hour periods from 00:00 UTC), market orders at the next open, the script's own quantities, pyramiding 15, commission / slippage / margin off.
4-hour EMA(200) of the period closes mapped with lookahead ON (each chart bar sees its period's finished value). Sniper long: ADX > 25, close crossing over the previous bar's 40-bar highest high, SMA5 - SMA35 > 0, close over the H4 EMA (short mirrored). While flat: one unit; while long with ADX > 20 and the close below the last entry close by the recovery distance (above for shorts), a recovery entry of multiplier^count units (the count resets when flat).
Open profit = sum over open lots of (close - entry) x quantity x direction at the signal close; it closes everything at the cycle target or when it is at or under the drawdown limit (percent of the initial capital, negative). Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too.
Variants: defaults with ADX/EMA as is on a smaller recovery distance; step 10, multiplier 1.3, target 60, drawdown 2 %."""
import numpy as np

from indep import bars, compare_q, np_cross_over, np_cross_under, np_dmi, np_ema, np_periods, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "lv5jFTZN"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    pid, last_of = np_periods(df, 240, start_minutes=0, tz="UTC")
    h4 = np_ema(c[last_of], 200)[pid]
    _, _, adx = np_dmi(h, l, c, 14)
    ewo = np_sma(c, 5) - np_sma(c, 35)
    hh = np.array([h[i - 39:i + 1].max() if i >= 39 else np.nan for i in range(n)])
    ll = np.array([l[i - 39:i + 1].min() if i >= 39 else np.nan for i in range(n)])
    up, dn = np_cross_over(c, np.r_[np.nan, hh[:-1]]), np_cross_under(c, np.r_[np.nan, ll[:-1]])
    S = dict(last=np.nan, cnt=0)
    ddl = -(10000 * p["dd"] / 100)

    def orders(i, info):
        out = []
        pos = info["pos"]
        op = sum((c[i] - x["ep"]) * x["q"] * x["d"] for x in info["lots"])
        with np.errstate(invalid="ignore"):
            ls = adx[i] > 25 and bool(up[i]) and ewo[i] > 0 and c[i] > h4[i]
            ss = adx[i] > 25 and bool(dn[i]) and ewo[i] < 0 and c[i] < h4[i]
            if op <= ddl and pos != 0:
                out.append(("close_all",))
                S.update(cnt=0, last=np.nan)
            if pos == 0:
                S["cnt"] = 0
                if ls:
                    out.append(("entry", "L", 1, 1.0))
                    S["last"] = c[i]
                elif ss:
                    out.append(("entry", "S", -1, 1.0))
                    S["last"] = c[i]
            if pos > 0 and c[i] < S["last"] - p["step"] and adx[i] > 20:
                S["cnt"] += 1
                out.append(("entry", "L_Rec%d" % S["cnt"], 1, p["mult"] ** S["cnt"]))
                S["last"] = c[i]
            if pos < 0 and c[i] > S["last"] + p["step"] and adx[i] > 20:
                S["cnt"] += 1
                out.append(("entry", "S_Rec%d" % S["cnt"], -1, p["mult"] ** S["cnt"]))
                S["last"] = c[i]
            if op >= p["tp"]:
                out.append(("close_all",))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=15)
    sym = SymbolInfo.make("BINANCE:XAUUSDT", "crypto", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(step=24.0, mult=1.6, tp=200.0, dd=5.0)


def check():
    df = bars(30000, seed=351, freq="15min")
    base = df["close"].iloc[0]
    for k in ("open", "high", "low", "close"):
        df[k] = 2000 * (df[k] / base) ** 0.1
    msgs, allok = [], True
    cases = (({"Distancia de Recuperación ($)": 8.0, "Objetivo de Ganancia Ciclo ($)": 60.0}, dict(step=8.0, tp=60.0)),
             ({"Distancia de Recuperación ($)": 10.0, "Multiplicador Progresivo": 1.3, "Objetivo de Ganancia Ciclo ($)": 60.0, "Max Open Loss (% of Capital)": 2.0}, dict(step=10.0, mult=1.3, tp=60.0, dd=2.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
