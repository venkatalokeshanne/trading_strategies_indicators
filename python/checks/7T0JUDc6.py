"""Independent check — Tomukas Premium Signals (7T0JUDc6): hourly bars, process_orders_on_close (signals fill at that bar's close, reversing). Long: close > EMA50 > EMA200, low <= EMA25 or EMA50, EMA3/EMA6 cross, MACD(12,26,9) cross,
RSI14 > 55, +DI > -DI, ADX14 > 22, volume > SMA20; short mirrored. v6 short-circuit: the EMA cross runs only when trend + pullback hold, the MACD cross only when the EMA cross was true as well, each against its own last
evaluated values (LESSONS P4/P5). The script reads the position BEFORE the bar's close fills, so the bracket (avg -/+ 1.2 ATR stop, +/- 1.8 ATR limit) is first issued on the bar after the fill and the levels at bar i
are those of bar i-1's close (trail_points alone never trails). Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_adx, np_atr, np_dmi, np_ema, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "7T0JUDc6"


def check():
    df = bars(120000, seed=239, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    e3, e6, e25, e50, e200 = (np_ema(c, k) for k in (3, 6, 25, 50, 200))
    macd = np_ema(c, 12) - np_ema(c, 26)
    sig = np_ema(macd, 9)
    from indep import np_rsi
    rsi, atr = np_rsi(c, 14), np_atr(h, l, c, 14)
    pdi, mdi, adx = np_dmi(h, l, c, 14)
    vok = v > np_sma(v, 20)
    with np.errstate(invalid="ignore"):
        bt, st_ = (c > e50) & (e50 > e200), (c < e50) & (e50 < e200)
        lp, sp = (l <= e25) | (l <= e50), (h >= e25) | (h >= e50)
        pre_l = bt & lp
        pre_s = st_ & sp
        rest_l = (rsi > 55) & (pdi > mdi) & (adx > 22) & vok
        rest_s = (rsi < 45) & (mdi > pdi) & (adx > 22) & vok
    pa = dict(lf=np.nan, ls=np.nan, mf=np.nan, ms=np.nan, sf=np.nan, ss=np.nan, tf=np.nan, ts=np.nan)   # last evaluated pairs per call site
    ep_now, avg_close, poscl = {}, np.full(n, np.nan), np.zeros(n)

    def orders(i, pos):
        poscl[i] = pos
        avg_close[i] = ep_now.get(i, np.nan) if pos != 0 else np.nan
        ls_ = ss_ = False
        if pre_l[i]:
            x = bool(e3[i] > e6[i] and pa["lf"] <= pa["ls"])
            pa["lf"], pa["ls"] = e3[i], e6[i]
            if x:
                y = bool(macd[i] > sig[i] and pa["mf"] <= pa["ms"])
                pa["mf"], pa["ms"] = macd[i], sig[i]
                ls_ = y and rest_l[i]
        if pre_s[i]:
            x = bool(e3[i] < e6[i] and pa["sf"] >= pa["ss"])
            pa["sf"], pa["ss"] = e3[i], e6[i]
            if x:
                y = bool(macd[i] < sig[i] and pa["tf"] >= pa["ts"])
                pa["tf"], pa["ts"] = macd[i], sig[i]
                ss_ = y and rest_s[i]
        out = []
        if ls_:
            out += [("close", -1), ("entry", 1)]
        if ss_:
            out += [("close", 1), ("entry", -1)]
        return out

    def level(k):
        def fn(i, pos, ep, eb):
            ep_now[i] = ep
            if i == 0 or poscl[i - 1] != pos or np.isnan(avg_close[i - 1]) or np.isnan(atr[i - 1]):
                return None
            a, r = avg_close[i - 1], atr[i - 1]
            return (a - pos * r * 1.2) if k == 0 else (a + pos * r * 1.8)
        return fn

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=level(0), target=level(1), on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
