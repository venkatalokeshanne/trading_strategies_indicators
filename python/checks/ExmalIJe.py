"""Independent check — Weekly Strangle Seller (ExmalIJe): 15-minute bars on an Asia/Kolkata chart (session 09:15-15:30, 24 h synthetic data), process_orders_on_close, default pyramiding. On a Monday / Tuesday entry day (exchange-timezone weekday) inside the IST entry window 10:00-14:00, once per week (the flag resets on the first bar of a Monday), with strike width >= 3 % of the close, no RSI14 extreme (<30 or >70) and (SuperTrend neutral or width >= 4 %): short "SellCE" then long "SellPE" at the close - the second opposite entry reverses the first (a zero-length short trade), leaving the long. Levels: center = session VWAP(hlc3) (reset on the trading day starting 09:15) or EMA20; CE = ceil((center + 1.8 ATR14) / 100) x 100, PE = floor((center - 1.8 ATR14) / 100) x 100; SL_CE = CE + (CE - center), SL_PE = PE - (center - PE). Close the position (both ids) when high >= SL_CE, low <= SL_PE, on the expiry day (Thursday) bar starting 15:15, or the Friday bar starting 15:20 (never reached with 15-minute bars). Commission / slippage / margin off on the pinelib side. Variants: VWAP centre with default filters, EMA20 centre with Wednesday entries and RSI filter off, ST filter off with min width 2.5."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_rsi, np_supertrend, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "ExmalIJe"


def one(df, params, vwap_c, wed, rsif, stf, minw):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    ist = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Asia/Kolkata")
    m = (ist.dt.hour * 60 + ist.dt.minute).to_numpy()
    dow = ist.dt.dayofweek.to_numpy()      # Monday = 0
    day = (ist.dt.tz_localize(None) - pd.Timedelta(minutes=555)).dt.date.to_numpy()
    hl3 = (h + l + c) / 3
    vw = np.zeros(n)
    pv = vv = 0.0
    for i in range(n):
        if i == 0 or day[i] != day[i - 1]:
            pv = vv = 0.0
        pv += hl3[i] * v[i]
        vv += v[i]
        vw[i] = pv / vv
    ema20, atr, rsi = np_ema(c, 20), np_atr(h, l, c, 14), np_rsi(c, 14)
    _, sd = np_supertrend(h, l, c, 2.0, 10)
    S = dict(taken=False, it=False, sce=0.0, spe=0.0)

    def orders(i, pos):
        out = []
        if i == 0 or np.isnan(atr[i]):
            return out
        center = vw[i] if vwap_c else ema20[i]
        ce = np.ceil((center + atr[i] * 1.8) / 100) * 100
        pe = np.floor((center - atr[i] * 1.8) / 100) * 100
        width = (ce - pe) / c[i] * 100
        bull, bear = sd[i] < 0, sd[i] > 0
        rbad = rsif and (rsi[i] > 70 or rsi[i] < 30)
        entry_day = dow[i] == 0 or dow[i] == 1 or (wed and dow[i] == 2)
        inwin = 600 <= m[i] < 840
        if dow[i] == 0 and dow[i - 1] != 0:
            S["taken"] = False
        ok = width >= minw and (not stf or (not bull and not bear) or width >= 4.0) and not rbad
        if entry_day and inwin and not S["taken"] and ok and not S["it"]:
            out += [("entry", -1), ("entry", 1)]
            S["sce"] = ce + (ce - center) * 1.0
            S["spe"] = pe - (center - pe) * 1.0
            S["it"] = True
            S["taken"] = True
        exits = []
        if S["it"] and h[i] >= S["sce"]:
            exits.append("ce")
            S["it"] = False
        if S["it"] and l[i] <= S["spe"]:
            exits.append("pe")
            S["it"] = False
        if S["it"] and dow[i] == 3 and 915 <= m[i] < 930:
            exits.append("exp")
            S["it"] = False
        if exits and pos != 0:
            out += [("close", 1), ("close", -1)]
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, on_close=True)
    sym = SymbolInfo.make("NSE:NIFTY", "stock", qty_step=1e-9, timezone="Asia/Kolkata", session="0915-1530")
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "commission_value": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(20000, seed=818, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 200 * (df[k] / 100) ** 0.4 * 100
    msgs, allok = [], True
    cases = (({}, (True, False, True, True, 3.0)),
             ({"VWAP as Center": False, "Enter on Wednesday": True, "RSI Filter": False}, (False, True, False, True, 3.0)),
             ({"SuperTrend Filter": False, "Min Width % (skip if narrow)": 2.5}, (True, False, True, False, 2.5)))
    for params, args in cases:
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
