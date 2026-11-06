"""Independent check — BTCUSDT 4H Breakout Retest Strategy (zMwHN2Uu): 4-hour bars around 85 000, market entries at the next open, one position, bracket (stop 1.5 %, target 3 % of the signal close) placed with the entry and working from the fill bar. Levels: the manual inputs from the "active from" date, before it swing-based auto levels (last confirmed 5/5 pivot high = resistance, pivot low = support, the "flip" = the resistance last crossed up by the close; zone [flip x 0.99, flip], floor flip x 0.973). Retest long: close above the zone top, bullish, dipped to it (low <= top or previous close <= top), came from above (highest close of 8 bars, 6 bars ago, above the top), the lowest low of 6 bars not under the floor, RSI14 in (42, 72), MACD histogram > 0 or rising, not > 6 % over SMA50, close within 1 % of the level. Breakout long: crossing the resistance (zone top or breakout resistance) with RSI in (55, 80), histogram > 0, close > SMA50. Short: cross down of the break level, RSI in (20, 45), histogram < 0, close < SMA50. Cooldown 6 bars after an entry or a flat bar. Margin off on the pinelib side.
Variants: defaults (auto levels before 21 Sep 2026), manual levels active from the start of the data, auto levels everywhere with shorts off and a 3-bar cooldown."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, np_rsi, np_sma, run_conversion, simulate

TV_ID = "zMwHN2Uu"
LEVELS_FROM = 1789948800000


def ema_na(x, n):
    out = np.full(len(x), np.nan)
    idx = np.flatnonzero(~np.isnan(x))
    if len(idx) < n:
        return out
    s = idx[0] + n - 1
    out[s] = x[idx[0]:s + 1].mean()
    k = 2.0 / (n + 1)
    for i in range(s + 1, len(x)):
        out[i] = k * x[i] + (1 - k) * out[i - 1]
    return out


def one(df, params, mfrom, use_auto, shorts, cd):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    t = df["time"].to_numpy()
    n = len(c)
    rsi = np_rsi(c, 14)
    macd = np_ema(c, 12) - np_ema(c, 26)
    hist = macd - ema_na(macd, 9)
    sf, sl_ = np_sma(c, 50), np_sma(c, 200)
    ph, pl = np.full(n, np.nan), np.full(n, np.nan)
    for i in range(10, n):
        j = i - 5
        if h[j] > h[j - 5:j].max() and h[j] > h[j + 1:i + 1].max():
            ph[i] = h[j]
        if l[j] < l[j - 5:j].min() and l[j] < l[j + 1:i + 1].min():
            pl[i] = l[j]
    cmax8 = pd.Series(c).rolling(8).max().to_numpy()
    low6 = pd.Series(l).rolling(6).min().to_numpy()
    S = dict(res=np.nan, sup=np.nan, flip=np.nan, ltb=None, pp=0)
    lev = {}

    def up(i, v):
        return not np.isnan(v) and c[i] > v and c[i - 1] <= v

    def dn(i, v):
        return not np.isnan(v) and c[i] < v and c[i - 1] >= v

    def orders(i, pos):
        out = []
        if i < 1:
            return out
        if not np.isnan(ph[i]):
            S["res"] = ph[i]
        if not np.isnan(pl[i]):
            S["sup"] = pl[i]
        if up(i, S["res"]):
            S["flip"] = S["res"]
        auto = use_auto or t[i] < mfrom
        zt = S["flip"] if auto else 85300.0
        fl = S["flip"] * (1 - 0.027) if auto else 83000.0
        r1 = np.nan if auto else 85300.0
        r2 = S["res"] if auto else 87400.0
        bu = S["sup"] if auto else 82600.0
        inw = auto or t[i] >= mfrom
        pr = cmax8[i - 6] if i >= 6 else np.nan
        zok = not np.isnan(zt) and not np.isnan(fl)
        with np.errstate(invalid="ignore"):
            retest_ev = zok and c[i] > zt and c[i] > o[i] and (l[i] <= zt or c[i - 1] <= zt)
            came = zok and not np.isnan(pr) and pr > zt
            ncol = zok and low6[i] >= fl
            b1, b2 = up(i, r1), up(i, r2)
            bl = r2 if b2 else r1
            bd = dn(i, bu)
            mup = hist[i] > 0 or hist[i] > hist[i - 1]
            rmom = 42 < rsi[i] < 72 and mup
            bmom = 55 < rsi[i] < 80 and hist[i] > 0 and (np.isnan(sf[i]) or c[i] > sf[i])
            smom = 20 < rsi[i] < 45 and hist[i] < 0 and (np.isnan(sf[i]) or c[i] < sf[i])
            nxu = np.isnan(sf[i]) or c[i] < sf[i] * 1.06
            nxd = np.isnan(sf[i]) or c[i] > sf[i] * 0.94
            cr = not np.isnan(zt) and c[i] <= zt * 1.01
            cb = not np.isnan(bl) and c[i] <= bl * 1.01
            cs = not np.isnan(bu) and c[i] >= bu * 0.99
        if pos == 0 and S["pp"] != 0:
            S["ltb"] = i
        S["pp"] = pos
        cok = S["ltb"] is None or i - S["ltb"] >= cd
        can = inw and pos == 0 and cok
        rl = can and retest_ev and came and ncol and rmom and nxu and cr
        bl_ = can and not rl and (b1 or b2) and bmom and nxu and cb
        ls = rl or bl_
        ss = shorts and can and not ls and bd and smom and nxd and cs
        if ls:
            lev[i] = (c[i] * (1 - 0.015), c[i] * (1 + 0.03))
            S["ltb"] = i
            out.append(("entry", 1))
        if ss:
            lev[i] = (c[i] * (1 + 0.015), c[i] * (1 - 0.03))
            S["ltb"] = i
            out.append(("entry", -1))
        return out

    stop = lambda i, pos, ep, eb: lev[eb - 1][0] if eb - 1 in lev else None
    tgt = lambda i, pos, ep, eb: lev[eb - 1][1] if eb - 1 in lev else None
    ref = simulate(o, h, l, c, orders, stop=stop, target=tgt)
    sym = SymbolInfo_crypto()
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="240", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def SymbolInfo_crypto():
    from pinelib import SymbolInfo
    return SymbolInfo.make("BINANCE:BTCUSDT", "crypto", qty_step=1e-9)


def check():
    df = bars(4000, seed=29, freq="4h")
    end = pd.Timestamp("2026-10-02", tz="UTC")
    start = end - pd.Timedelta(hours=4 * 4000)
    df["time"] = pd.date_range(start, periods=4000, freq="4h").as_unit("ms").asi8
    for k in ("open", "high", "low", "close"):
        df[k] = 85000 * (df[k] / 100) ** 0.2
    msgs, allok = [], True
    cases = (({}, LEVELS_FROM, False, True, 6),
             ({"Manual levels active from": int(df["time"].iloc[0])}, int(df["time"].iloc[0]), False, True, 6),
             ({"Use auto levels on all bars (ignore manual levels)": True, "Enable shorts": False, "Cooldown between trades (bars)": 3}, LEVELS_FROM, True, False, 3))
    for params, mfrom, ua, sh, cd in cases:
        ok, m = one(df, params, mfrom, ua, sh, cd)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
