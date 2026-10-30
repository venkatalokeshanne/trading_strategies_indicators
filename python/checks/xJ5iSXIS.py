"""Independent check — Tomukas Wave VWAP DCA Scalper PRO (xJ5iSXIS): 15-minute bars (24 h synthetic) of a stock-style symbol (VWAP restarting at 09:30 New York), process_orders_on_close (orders fill at the signal close), the script's own quantities (0.5, then 0.5 / 1 / 2 / 4 adds), pyramiding 4, commission / slippage / margin off.
Confirmation (long): close > EMA200, EMA50 > EMA200, close above the range filter [EMA-smoothed |change| with the Pine ternary chain], WaveTrend cross-up, RSI > 50 with volume over its 20-bar average, close > VWAP, momentum (RSI / MACD / EMA20), volume-profile node zone, close > previous high (short mirrored). Flat -> 0.5 unit and the DCA counter at 1;
each further step % against the first entry adds the next lot (counter advances even when the pyramiding limit rejects the 5th lot); the basket closes at the take-profit / drawdown percentage of the average price. Uses the quantity-aware bracket reference (indep.simulate_brackets, on_close), comparing quantities too.
Variants: filters relaxed (no VWAP / momentum / volume zone); additionally 0.3 % basket target and 0.5 % add step."""
import numpy as np

from indep import bars, compare_q, np_cross_over, np_cross_under, np_ema, np_rsi, np_sma, np_vwap, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "xJ5iSXIS"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    hlc3 = (h + l + c) / 3
    e200, e50, e20 = np_ema(c, 200), np_ema(c, 50), np_ema(c, 20)
    vw = np_vwap(df, hlc3)
    rb = np_ema(np.r_[np.nan, np.abs(np.diff(c))], 27)
    rs = np_ema(rb, 53) * 1.8
    rf = np.full(n, np.nan)
    prev = np.nan
    for i in range(n):
        pr = c[i] if np.isnan(prev) else prev
        if c[i] > pr:
            cur = pr if c[i] - rs[i] < pr else c[i] - rs[i]
        else:
            cur = pr if c[i] + rs[i] > pr else c[i] + rs[i]
        rf[i] = cur
        prev = cur
    esa = np_ema(hlc3, 9)
    dev = np_ema(np.abs(hlc3 - esa), 9)
    with np.errstate(invalid="ignore", divide="ignore"):
        wave = np_ema((hlc3 - esa) / (0.015 * dev), 6)
    ws = np_sma(wave, 3)
    wbu, wbd = np_cross_over(wave, ws), np_cross_under(wave, ws)
    rsi = np_rsi(c, 14)
    macd = np_ema(c, 12) - np_ema(c, 26)
    msig = np_ema(macd, 9)
    vma = np_sma(v, 20)
    hv = np.array([v[i] == v[i - 79:i + 1].max() if i >= 79 else False for i in range(n)])
    S = dict(node=np.nan, dca=0, fe=np.nan)
    Q = (0.5, 1, 2, 4)

    def orders(i, info):
        out = []
        pos, avg = info["pos"], info["avg"]
        if hv[i]:
            S["node"] = hlc3[i]
        with np.errstate(invalid="ignore"):
            near = (not np.isnan(S["node"])) and abs(c[i] - S["node"]) / c[i] < 0.003
            vzl = (not p["vz"]) or np.isnan(S["node"]) or c[i] > S["node"] or near
            vzs = (not p["vz"]) or np.isnan(S["node"]) or c[i] < S["node"] or near
            vl = (not p["vwap"]) or c[i] > vw[i]
            vs = (not p["vwap"]) or c[i] < vw[i]
            mbu = (not p["mom"]) or (rsi[i] > 50 and macd[i] > msig[i] and c[i] > e20[i])
            mbd = (not p["mom"]) or (rsi[i] < 50 and macd[i] < msig[i] and c[i] < e20[i])
            vok = v[i] > vma[i]
            hp, lp = (h[i - 1], l[i - 1]) if i > 0 else (np.nan, np.nan)
            cl = c[i] > e200[i] and e50[i] > e200[i] and c[i] > rf[i] and bool(wbu[i]) and rsi[i] > 50 and vok and vl and mbu and vzl and c[i] > hp
            cs = c[i] < e200[i] and e50[i] < e200[i] and c[i] < rf[i] and bool(wbd[i]) and rsi[i] < 50 and vok and vs and mbd and vzs and c[i] < lp
        if pos == 0:
            S.update(dca=0, fe=np.nan)
        if cl and pos == 0 and info["n"] == 0:
            out.append(("entry", "L1", 1, 0.5))
            S.update(fe=c[i], dca=1)
        if cs and pos == 0 and info["n"] == 0:
            out.append(("entry", "S1", -1, 0.5))
            S.update(fe=c[i], dca=1)
        st = p["step"]
        la = [pos > 0 and S["dca"] == k and c[i] <= S["fe"] * (1 - st * k / 100) for k in (1, 2, 3, 4)]
        sa = [pos < 0 and S["dca"] == k and c[i] >= S["fe"] * (1 + st * k / 100) for k in (1, 2, 3, 4)]
        for k in range(4):
            if la[k]:
                out.append(("entry", "L%d" % (k + 2), 1, Q[k]))
                S["dca"] = k + 2
        for k in range(4):
            if sa[k]:
                out.append(("entry", "S%d" % (k + 2), -1, Q[k]))
                S["dca"] = k + 2
        if pos > 0 and c[i] >= avg * (1 + p["tp"] / 100):
            out.append(("close_all",))
        if pos < 0 and c[i] <= avg * (1 - p["tp"] / 100):
            out.append(("close_all",))
        if pos > 0 and c[i] <= avg * (1 - 4.0 / 100):
            out.append(("close_all",))
        if pos < 0 and c[i] >= avg * (1 + 4.0 / 100):
            out.append(("close_all",))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=4, on_close=True)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(vwap=True, mom=True, vz=True, tp=0.6, step=1.0)


def check():
    df = bars(60000, seed=591, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    off = {"Use VWAP Filter": False, "Use Momentum Confirm": False, "Use Volume Profile Zone": False}
    o0 = dict(vwap=False, mom=False, vz=False)
    msgs, allok = [], True
    cases = ((dict(off), o0), ({**off, "Basket TP %": 0.3, "DCA Add Every % Against": 0.5}, dict(o0, tp=0.3, step=0.5)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
