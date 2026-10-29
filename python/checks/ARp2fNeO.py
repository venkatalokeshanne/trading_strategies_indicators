"""Independent check — New Era Strategy 1.0 (ARp2fNeO): 5-minute bars on an Asia/Kolkata chart. Formation (inside 09:15-15:00): short ("PE") when EMA9-smoothed ordering SMA9(EMA33) < EMA33 < HMA27 < HMA22 < HMA18 with RSI5 > 65, SMA5(RSI) > 60, CCI14 > 100,
SMA5(CCI) > 80; long ("CE") mirrored (RSI < 25 / 30, CCI < -50 / -20). The setup candle (low, high) is stored; re-based on later candles while the close stays inside it; entry when the close breaks the far side (below the low for
shorts): stop = min(high, previous high) (max of lows for longs), target = 2 x stop distance, both placed with the entry and working from the fill bar. A short may open while a long is open (and vice versa): entries reverse. Flags
reset when flat at a script run; longs only are closed in the 15:10-15:15 window (the original tests position_size > 0). Variants: default and a 1.5 % cap on the stop distance (stop -> candle extreme, else no trade)."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cci, np_ema, np_rsi, np_sma, np_wma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "ARp2fNeO"


def hma(x, n):
    return np_wma(2 * np_wma(x, n // 2) - np_wma(x, n), int(np.floor(np.sqrt(n))))


def one(df, cap):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ist = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Asia/Kolkata")
    m = (ist.dt.hour * 60 + ist.dt.minute).to_numpy()
    trade_t = (m >= 555) & (m < 900)
    exit_t = (m >= 910) & (m < 915)
    rsi = np_rsi(c, 5)
    rs = np_sma(rsi, 5)
    cci = np_cci(c, 14)
    cs = np_sma(cci, 5)
    e33 = np_ema(c, 33)
    es = np_sma(e33, 9)
    h18, h22, h27 = hma(c, 18), hma(c, 22), hma(c, 27)
    with np.errstate(invalid="ignore"):
        fpe = (es < e33) & (e33 < h27) & (h27 < h22) & (h22 < h18) & (rsi > 65) & (rs > 60) & (cci > 100) & (cs > 80) & trade_t
        fce = (es > e33) & (e33 > h27) & (h27 > h22) & (h22 > h18) & (rsi < 25) & (rs < 30) & (cci < -50) & (cs < -20) & trade_t
    S = dict(sl_=np.nan, sh_=np.nan, apE=False, aCE=False, rPE=False, rCE=False)
    lev = {}

    def orders(i, pos):
        out = []
        if pos > 0 and exit_t[i]:
            out.append(("close", 1))
        if pos == 0:
            S["rPE"] = S["rCE"] = False
        if not S["rPE"] and trade_t[i]:
            if fpe[i]:
                if i > 0 and fpe[i - 1]:
                    if (h[i] > S["sh_"] or l[i] < S["sl_"]) and c[i] > S["sl_"]:
                        S["sl_"], S["sh_"], S["apE"] = l[i], h[i], True
                else:
                    S["sl_"], S["sh_"], S["apE"] = l[i], h[i], True
            if S["apE"] and c[i] > S["sl_"]:
                if h[i] > S["sh_"] or l[i] < S["sl_"] or (l[i] > S["sl_"] and h[i] < S["sh_"]):
                    S["sl_"], S["sh_"] = l[i], h[i]
            if S["apE"] and c[i] < S["sl_"]:
                sl = min(h[i - 1], h[i])
                slp = sl - c[i]
                if cap > 0:
                    mx = c[i] / 100 * cap
                    if slp > mx:
                        sl = h[i]
                        slp = sl - c[i]
                        if slp > mx:
                            sl = 0
                if sl > 0:
                    out.append(("entry", -1))
                    lev[i] = (sl, c[i] - 2 * slp)
                    S["rPE"], S["apE"], S["sl_"], S["sh_"] = True, False, np.nan, np.nan
        if not S["rCE"] and trade_t[i]:
            if fce[i]:
                if i > 0 and fce[i - 1]:
                    if (l[i] < S["sl_"] or h[i] > S["sh_"]) and c[i] < S["sh_"]:
                        S["sl_"], S["sh_"], S["aCE"] = l[i], h[i], True
                else:
                    S["sl_"], S["sh_"], S["aCE"] = l[i], h[i], True
            if S["aCE"] and c[i] < S["sh_"]:
                if l[i] < S["sl_"] or h[i] > S["sh_"] or (h[i] < S["sh_"] and l[i] > S["sl_"]):
                    S["sl_"], S["sh_"] = l[i], h[i]
            if S["aCE"] and c[i] > S["sh_"]:
                sl = min(l[i - 1], l[i])
                slp = c[i] - sl
                if cap > 0:
                    mx = c[i] / 100 * cap
                    if slp > mx:
                        sl = l[i]
                        slp = c[i] - sl
                        if slp > mx:
                            sl = 0
                if sl > 0:
                    out.append(("entry", 1))
                    lev[i] = (sl, c[i] + 2 * slp)
                    S["rCE"], S["aCE"], S["sl_"], S["sh_"] = True, False, np.nan, np.nan
        return out

    stop = lambda i, pos, ep, eb: lev[eb - 1][0] if eb - 1 in lev else None
    tgt = lambda i, pos, ep, eb: lev[eb - 1][1] if eb - 1 in lev else None
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt)
    sym = SymbolInfo.make("NSE:NIFTY", "stock", qty_step=1e-9, timezone="Asia/Kolkata", session="0915-1530")
    params = {"SL Max Points %": cap} if cap else {}
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"cap={cap}: {d} (got {len(ref)})"


def check():
    df = bars(40000, seed=561, freq="5min")
    msgs, allok = [], True
    for cap in (0.0, 1.5):
        ok, msg = one(df, cap)
        allok &= ok
        msgs.append(msg)
    return allok, " | ".join(msgs)
