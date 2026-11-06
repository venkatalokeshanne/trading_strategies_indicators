"""Independent check — 82 TRADE v8.4 (RcF7t6Am): hourly bars, one position, market entries at the next open, the stop kept as an exit order from the first script run that sees the position (so it works from the bar after the fill). Sweep: latest pivot low (5 left / 2 right, strict) latched; bar low < it, close > it, bullish (short mirrored with pivot highs);
volume > 1.2 x SMA20(volume); closing position (close - low) / range >= 0.65 (short (high - close) / range); bar start in 15:00-03:00 Taipei; flat. Initial stop = sweep bar low - tick (high + tick), risk R = fill price - stop. Per bar in a trade: 1.5 R in the money -> stop to break-even then max with close - 3 ATR; a climax bar (volume > 2.5 x SMA, wick >= 1.5 x body)
with >= 1 R open profit tightens to close - ATR; 15 bars after the fill and under water -> close at the next open. Variants: default; capitulation exit = close ("直接平倉"). Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "RcF7t6Am"
K, R = 5, 2


def one(df, params, cap_close):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    atr, vma = np_atr(h, l, c, 14), np_sma(v, 20)
    ph, pl = np.full(n, np.nan), np.full(n, np.nan)
    for i in range(K + R, n):
        j = i - R
        if h[j] > h[j - K:j].max() and h[j] > h[j + 1:i + 1].max():
            ph[i] = h[j]
        if l[j] < l[j - K:j].min() and l[j] < l[j + 1:i + 1].min():
            pl[i] = l[j]
    tp = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Asia/Taipei")
    m = (tp.dt.hour * 60 + tp.dt.minute).to_numpy()
    sess = (m >= 900) | (m < 180)
    S = dict(lsh=np.nan, lsl=np.nan, pl_=np.nan, ps=np.nan, stop=np.nan, risk=np.nan, ebar=None, trail=False, ep=np.nan)
    poscl = np.zeros(n)
    stop_arr = np.full(n, np.nan)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if not np.isnan(ph[i]):
            S["lsh"] = ph[i]
        if not np.isnan(pl[i]):
            S["lsl"] = pl[i]
        bull = (not np.isnan(S["lsl"])) and l[i] < S["lsl"] and c[i] > S["lsl"] and c[i] > o[i]
        bear = (not np.isnan(S["lsh"])) and h[i] > S["lsh"] and c[i] < S["lsh"] and c[i] < o[i]
        hv = v[i] > 1.2 * vma[i]
        rng = h[i] - l[i]
        bp = 0.0 if rng == 0 else (c[i] - l[i]) / rng
        sp = 0.0 if rng == 0 else (h[i] - c[i]) / rng
        if bull and sess[i] and hv and bp >= 0.65 and pos == 0:
            S["pl_"] = l[i] - 0.01
            if c[i] - S["pl_"] > 0:
                out.append(("entry", 1))
        if bear and sess[i] and hv and sp >= 0.65 and pos == 0:
            S["ps"] = h[i] + 0.01
            if S["ps"] - c[i] > 0:
                out.append(("entry", -1))
        prev = poscl[i - 1] if i else np.nan
        if pos > 0 and prev <= 0:
            S["stop"], S["risk"], S["ebar"], S["trail"] = S["pl_"], S["ep"] - S["pl_"], i, False
        if pos < 0 and prev >= 0:
            S["stop"], S["risk"], S["ebar"], S["trail"] = S["ps"], S["ps"] - S["ep"], i, False
        if pos == 0:
            S["stop"] = S["risk"] = np.nan
            S["ebar"], S["trail"] = None, False
        body = abs(c[i] - o[i])
        uw = h[i] - max(o[i], c[i])
        lw = min(o[i], c[i]) - l[i]
        cap_l = v[i] > 2.5 * vma[i] and uw >= body * 1.5
        cap_s = v[i] > 2.5 * vma[i] and lw >= body * 1.5
        a = S["ep"]
        if pos > 0:
            if not S["trail"] and c[i] >= a + S["risk"] * 1.5:
                S["trail"] = True
            if S["trail"]:
                S["stop"] = max(S["stop"], a)
                S["stop"] = max(S["stop"], c[i] - atr[i] * 3.0)
            if cap_l:
                pr = (c[i] - a) / S["risk"] if S["risk"] != 0 else np.nan
                if pr >= 1.0:
                    if cap_close:
                        out.append(("close", 1))
                    else:
                        S["stop"] = max(S["stop"], c[i] - atr[i])
            if S["ebar"] is not None and i - S["ebar"] >= 15 and c[i] < a:
                out.append(("close", 1))
            stop_arr[i] = S["stop"]
        elif pos < 0:
            if not S["trail"] and c[i] <= a - S["risk"] * 1.5:
                S["trail"] = True
            if S["trail"]:
                S["stop"] = min(S["stop"], a)
                S["stop"] = min(S["stop"], c[i] + atr[i] * 3.0)
            if cap_s:
                pr = (a - c[i]) / S["risk"] if S["risk"] != 0 else np.nan
                if pr >= 1.0:
                    if cap_close:
                        out.append(("close", -1))
                    else:
                        S["stop"] = min(S["stop"], c[i] + atr[i])
            if S["ebar"] is not None and i - S["ebar"] >= 15 and c[i] > a:
                out.append(("close", -1))
            stop_arr[i] = S["stop"]
        return out

    def stop(i, pos, ep, eb):
        S["ep"] = ep
        if i == 0 or eb >= i or poscl[i - 1] * pos <= 0 or np.isnan(stop_arr[i - 1]):
            return None
        return stop_arr[i - 1]

    with np.errstate(invalid="ignore", divide="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(40000, seed=681, freq="1h")
    msgs, allok = [], True
    for params, cc in (({}, False), ({"爆量反轉(CapExit)": "直接平倉"}, True)):
        ok, m = one(df, params, cc)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
