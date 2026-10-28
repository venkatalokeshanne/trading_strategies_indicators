"""Independent check — Gold NY ORB v19 (FJZvYKaB): 5-min New York bars shifted to start on 2024-01-02. Opening range = the 13:00-13:59 UTC bars of a weekday (New York calendar
weekday); the range / flags reset when the NEW TRADING DAY starts (09:30 New York), which falls inside that hour. Long breakout once per day between 14:00 and 16:30 UTC when the
range is <= 2.5 ATR, ATR is not above 2x its SMA20, the close breaks the range high from below on a green candle with volume > 1.5 x SMA20. Bracket 1 range stop / 2.5 range target
placed with the signal-bar entry (already working on the fill bar); longs are closed at the 20:00 UTC bar. Slippage (2 ticks) is 0 on both sides; margin off."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "FJZvYKaB"


def one(seed):
    df = bars(30000, seed=seed, freq="5min")
    df["time"] = df["time"] - df["time"].iloc[0] + int(pd.Timestamp("2024-01-02 00:00", tz="UTC").value // 1_000_000)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    ut = pd.to_datetime(df["time"], unit="ms", utc=True)
    ny = ut.dt.tz_convert("America/New_York")
    hh, mm = ut.dt.hour.to_numpy(), ut.dt.minute.to_numpy()
    wkd = (ny.dt.dayofweek < 5).to_numpy()
    key = (ny - pd.Timedelta(minutes=570)).dt.date.to_numpy()
    atr = np_atr(h, l, c, 14)
    vol_avg, atr_avg = np_sma(v, 20), np_sma(atr, 20)
    st = dict(oh=np.nan, ol=np.nan, ready=False, fired=False, sl=np.nan, tp=np.nan)
    poscl, lvl = np.zeros(n), []

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if i > 0 and key[i] != key[i - 1]:
            st.update(oh=np.nan, ol=np.nan, ready=False, fired=False)
        orp = wkd[i] and hh[i] == 13
        if orp:
            st["oh"] = h[i] if np.isnan(st["oh"]) else max(st["oh"], h[i])
            st["ol"] = l[i] if np.isnan(st["ol"]) else min(st["ol"], l[i])
        if (not orp) and (not np.isnan(st["oh"])) and (not st["ready"]) and hh[i] >= 14:
            st["ready"] = True
        rng = np.nan if (np.isnan(st["oh"]) or np.isnan(st["ol"])) else st["oh"] - st["ol"]
        entry_win = wkd[i] and hh[i] >= 14 and (hh[i] < 16 or (hh[i] == 16 and mm[i] <= 30))
        regime = atr[i] <= atr_avg[i] * 2.0
        ok = st["ready"] and not np.isnan(rng) and rng <= atr[i] * 2.5
        lb = (entry_win and ok and regime and not st["fired"] and c[i] > st["oh"] and c[i - 1] <= st["oh"]
              and c[i] > o[i] and v[i] > vol_avg[i] * 1.5) if i > 0 else False
        if lb:
            out.append(("entry", 1)); st["sl"], st["tp"] = c[i] - rng, c[i] + rng * 2.5; st["fired"] = True
        if wkd[i] and hh[i] == 20 and mm[i] == 0 and pos > 0:
            out.append(("close", 1))
        lvl.append((st["sl"], st["tp"]))
        return out

    def level(k):
        return lambda i, pos, ep, eb: lvl[i - 1][k] if i > 0 else None      # placed on the signal bar, so already working on the fill bar

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok, detail, len(ref)


def check():
    """The opening-range breakout is rare (once a day at most): run several data sets and require > 10 trades in total."""
    res = [one(sd) for sd in (166, 168, 169, 170, 171, 172, 173, 174)]
    total = sum(r[2] for r in res)
    bad = [r[1] for r in res if not r[0]]
    return (not bad) and total > 10, (bad[0] if bad else f"{total} trades identical over {len(res)} data sets") + f" (need >10 trades, got {total})"
