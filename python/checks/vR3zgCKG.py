"""Independent check — RR Master (vR3zgCKG): 5-min New York bars, start time = first bar (passed to pinelib), SL buffer scaled to the price level (passed to both sides). Long: low > EMA200, close > session VWAP of hlc3, ADX(14) > 30
and > SMA7(ADX), RSI7 crossing over RSI14, 8 bars since the last ENTRY (bar_index - lastTradeBar >= 8, lastTradeBar starts at 0); short mirrored. Signal bar issues entry + exit (stop = low -/+ buffer, limit = 1.7 R) when flat,
so the bracket works from the fill bar."""
import numpy as np

from indep import bars, compare, np_adx, np_cross_over, np_cross_under, np_ema, np_rsi, np_sma, np_vwap, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "vR3zgCKG"


def check():
    df = bars(60000, seed=223, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    buf = round(float(c.mean()) * 0.002, 4)
    e = np_ema(c, 200)
    vw = np_vwap(df, (h + l + c) / 3)
    adx = np_adx(h, l, c, 14)
    rf, rs = np_rsi(c, 7), np_rsi(c, 14)
    with np.errstate(invalid="ignore"):
        strong = (adx > 30) & (adx > np_sma(adx, 7))
        bsig = (l > e) & (c > vw) & strong & np_cross_over(rf, rs)
        ssig = (h < e) & (c < vw) & strong & np_cross_under(rf, rs)
    last = [0]
    lvl = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}

    def orders(i, pos):
        out = []
        if i - last[0] >= 8 and pos == 0:
            if bsig[i]:
                sl = l[i] - buf
                out.append(("entry", 1)); lvl[1] = (sl, c[i] + abs(c[i] - sl) * 1.7); last[0] = i
            if ssig[i]:
                sl = h[i] + buf
                out.append(("entry", -1)); lvl[-1] = (sl, c[i] - abs(sl - c[i]) * 1.7); last[0] = i
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: lvl[pos][0], target=lambda i, pos, ep, eb: lvl[pos][1])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params={"วันที่เริ่มทดสอบ": int(df["time"].iloc[0]), "ระยะเผื่อ SL (2.0 = 200 จุดทอง)": buf},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
