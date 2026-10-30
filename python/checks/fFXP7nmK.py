"""Independent check — Nils Version (fFXP7nmK), 15-minute bars (24 h synthetic, New York clock), market entries at the next open,
2 contracts. The opening range (bar opening 09:30-09:45 New York, rebuilt at the first bar of each New York day), the filters
(EMA 200 / 50, volume over its 20-bar SMA, ADX > 20, RSI < 70 / > 30, optional VWAP) and the two-trade-per-day counter are rebuilt in numpy;
every entry carries its stop (0.5 %), limit (R multiple) and trailing exit (activation price, offset 1.5 ATR in ticks), all taken from
the SIGNAL close, in the quantity-aware reference broker. A bar opening 11:00-11:05 closes the position."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_dmi, np_ema, np_rsi, np_sma, np_vwap, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "fFXP7nmK"
TICK = 0.01
QTY = 2.0


def reference(df, close_confirm=True, adx_f=True, rsi_f=True, trend=True, micro=True, vol_f=True, vwap_f=False, trailing=True,
              rr=2.0, tr_act=1.0, tr_mult=1.5, max_trades=2, adx_rising=False):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    day = ny.dt.date.to_numpy()
    e200, e50 = np_ema(c, 200), np_ema(c, 50)
    avg_vol = np_sma(v, 20)
    atr = np_atr(h, l, c, 14)
    rsi = np_rsi(c, 14)
    adx = np_dmi(h, l, c, 14)[2]
    vw = np_vwap(df, (h + l + c) / 3)
    S = dict(hi=np.nan, lo=np.nan, set=False, cnt=0)

    def orders(i, info):
        out = []
        pos = info["pos"]
        opening = 570 <= m[i] < 585
        prev_open = i > 0 and 570 <= m[i - 1] < 585 and day[i - 1] == day[i]
        start = opening and not prev_open
        if i > 0 and day[i] != day[i - 1]:
            S.update(hi=np.nan, lo=np.nan, set=False, cnt=0)
        if start:
            S.update(hi=h[i], lo=l[i], set=False, cnt=0)
        if opening:
            S["hi"] = max(S["hi"], h[i]) if not np.isnan(S["hi"]) else np.nan
            S["lo"] = min(S["lo"], l[i]) if not np.isnan(S["lo"]) else np.nan
        elif m[i] >= 585 and not np.isnan(S["hi"]):
            S["set"] = True
        in_win = 570 <= m[i] < 660
        eod = 660 <= m[i] < 665
        c1 = c[i - 1] if i else np.nan
        if close_confirm:
            sig_l = c[i] > S["hi"] and c1 <= S["hi"]
            sig_s = c[i] < S["lo"] and c1 >= S["lo"]
        else:
            sig_l = i > 0 and c[i] > S["hi"] and c1 <= S["hi"]
            sig_s = i > 0 and c[i] < S["lo"] and c1 >= S["lo"]
        adx_ok = (not adx_f) or (adx[i] > 20 and ((not adx_rising) or adx[i] > adx[i - 1]))
        volc = (not vol_f) or v[i] > avg_vol[i]
        tl = ((not trend) or c[i] > e200[i]) and ((not micro) or c[i] > e50[i])
        ts = ((not trend) or c[i] < e200[i]) and ((not micro) or c[i] < e50[i])
        vl = (not vwap_f) or c[i] > vw[i]
        vs = (not vwap_f) or c[i] < vw[i]
        rl = (not rsi_f) or rsi[i] < 70
        rs = (not rsi_f) or rsi[i] > 30
        can = in_win and S["set"] and not opening and pos == 0 and S["cnt"] < max_trades
        if can:
            off = tr_mult * atr[i] / TICK
            risk = c[i] * 0.005
            for d, sig, ok, name in ((1, sig_l, volc and adx_ok and tl and vl and rl, "Long"),
                                     (-1, sig_s, volc and adx_ok and ts and vs and rs, "Short")):
                if sig and ok:
                    out.append(("entry", name, d, QTY))
                    stop, lim = c[i] * (1 - d * 0.005), c[i] + d * risk * rr
                    if trailing:
                        out.append(("exit", f"Exit {name}", name, None, stop, lim, None, c[i] + d * risk * tr_act, off))
                    else:
                        out.append(("exit", f"Exit {name}", name, None, stop, lim))
                    S["cnt"] += 1
        if eod and pos != 0:
            out.append(("close_all",))
        return out

    return simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=TICK, qty_step=1e-9)


def check():
    df = bars(14000, seed=31, freq="15min")
    lc = np.log(df["close"].to_numpy() / 100)
    det = lc - np.polyval(np.polyfit(np.arange(len(lc)), lc, 1), np.arange(len(lc)))
    rel = {k: df[k].to_numpy() / df["close"].to_numpy() for k in ("open", "high", "low", "close")}
    for k in rel:
        df[k] = 100 * np.exp(0.4 * det) * rel[k] ** 0.4
    sym = SymbolInfo.make("CME_MINI:NQ1!", "stock", qty_step=1e-9)
    ov = {"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}
    cases = (({"ADX Trend Filter (min strength)": False, "RSI Filter (Avoid Overextended)": False,
               "EMA 200 Trend Filter": False, "EMA 50 Micro Trend Filter": False, "Volume Filter (> 20 SMA)": False},
              dict(adx_f=False, rsi_f=False, trend=False, micro=False, vol_f=False)),
             ({}, {}),
             ({"Close Confirmation (candle must CLOSE beyond range)": False, "Enable Trailing Stop": False, "Risk/Reward Ratio": 1.5,
               "ADX Trend Filter (min strength)": False, "Volume Filter (> 20 SMA)": False, "VWAP Bias Filter": True, "Max Trades per Day": 3},
              dict(close_confirm=False, trailing=False, rr=1.5, adx_f=False, vol_f=False, vwap_f=True, max_trades=3)))
    msgs, ok_all = [], True
    for params, kw in cases:
        ref = reference(df, **kw)
        ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides=ov), ref)
        ok_all = ok_all and ok and len(ref) > (12 if kw or not params else 3)
        msgs.append(f"{d} (got {len(ref)})")
    return ok_all, " | ".join(msgs)
