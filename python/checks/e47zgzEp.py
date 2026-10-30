"""Independent check — Full Session Trading System (e47zgzEp): 5-min continuous bars. UTC windows: Asia 00-06, London 07-10, New York 13-16. Score = [EMA50 > EMA200 and 15m EMA50 > 15m EMA200 (lookahead off)] + [low < lowest low of the previous 10 bars] + [RSI14 > 50] + [close < EMA50] + [bullish candle]
(mirror for sells), trend session entries need >= 3; Asia entries need close <= Asia low + 0.2 ATR with RSI < 35 (sell: close >= Asia high - 0.2 ATR and RSI > 65), the Asia range accumulating from the session's first bar (a new session starts at the first bar even on bar 0).
One trade at a time; stop = close -/+ 1.2 ATR14, target = RR 1.8 from that, fixed at the signal bar."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_periods, np_rsi, np_security_lookahead_off, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "e47zgzEp"


def check():
    df = bars(16000, seed=105, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    hr = pd.to_datetime(df["time"], unit="ms", utc=True).dt.hour.to_numpy()
    asia = hr < 6
    trend_s = ((hr >= 7) & (hr < 10)) | ((hr >= 13) & (hr < 16))
    e50, e200, rsi, atr = np_ema(c, 50), np_ema(c, 200), np_rsi(c, 14), np_atr(h, l, c, 14)
    pid, last_of = np_periods(df, 15)
    pc = np.array([c[last_of & (pid == k)][0] for k in range(pid[-1] + 1)])
    h50 = np_security_lookahead_off(np_ema(pc, 50), pid, last_of)
    h200 = np_security_lookahead_off(np_ema(pc, 200), pid, last_of)
    pl = np.r_[np.nan, pd.Series(l).rolling(10).min().to_numpy()[:-1]]
    ph = np.r_[np.nan, pd.Series(h).rolling(10).max().to_numpy()[:-1]]
    lvl = {}
    st = dict(ah=np.nan, al=np.nan, prev=False)

    def orders(i, pos):
        out = []
        if asia[i] and not st["prev"]:
            st["ah"], st["al"] = h[i], l[i]
        elif asia[i]:
            st["ah"], st["al"] = max(st["ah"], h[i]), min(st["al"], l[i])
        st["prev"] = asia[i]
        with np.errstate(invalid="ignore"):
            bc = sum(map(int, [e50[i] > e200[i] and h50[i] > h200[i], l[i] < pl[i], rsi[i] > 50, c[i] < e50[i], c[i] > o[i]]))
            sc = sum(map(int, [e50[i] < e200[i] and h50[i] < h200[i], h[i] > ph[i], rsi[i] < 50, c[i] > e50[i], c[i] < o[i]]))
            nl = c[i] <= st["al"] + atr[i] * 0.2
            nh = c[i] >= st["ah"] - atr[i] * 0.2
            buy = (trend_s[i] and bc >= 3) or (asia[i] and nl and rsi[i] < 35)
            sell = (trend_s[i] and sc >= 3) or (asia[i] and nh and rsi[i] > 65)
        if buy and pos == 0:
            sl = c[i] - atr[i] * 1.2
            lvl[1] = (sl, c[i] + (c[i] - sl) * 1.8)
            out.append(("entry", 1))
        if sell and pos == 0:
            sl = c[i] + atr[i] * 1.2
            lvl[-1] = (sl, c[i] - (sl - c[i]) * 1.8)
            out.append(("entry", -1))
        return out

    def stop(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][0]

    def target(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
