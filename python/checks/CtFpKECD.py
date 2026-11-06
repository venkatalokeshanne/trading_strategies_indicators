"""Independent check — Shinobi HA Stratégia v3 (CtFpKECD): 15-minute bars, process_orders_on_close, one position, bracket (stop = HA low / high of the signal bar, target = close +/- rr x distance) placed with the entry and working from the next bar. Heikin-Ashi bars (ha_open seeded (o+c)/2); sell/buy setup = two same-colour HA bars with no lower/upper wick (wick <= 3 % of the range), a HA doji now (body <= 20 % of the range and both wicks >= 0.3 body) whose range is bigger than the bar before; direction by SuperTrend (3.44, 15) + ADX >= 22 + session 17:00-20:00 Budapest + volume >= EMA20(volume). Structure filter variants: Swing HL (last two confirmed HA pivots), LinReg channel (OLS over 100 closes, residual-deviation bands),
ATR channel (EMA50 of HA close +/- 2 ATR50) and Donchian (20) midpoint."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_dmi, np_ema, np_supertrend, run_conversion, simulate

TV_ID = "CtFpKECD"


def one(df, params, ftype, dm=0.2, wt=0.03, am=22.0, usevol=True):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    hc = (o + h + l + c) / 4
    ho = np.zeros(n)
    ho[0] = (o[0] + c[0]) / 2
    for i in range(1, n):
        ho[i] = (ho[i - 1] + hc[i - 1]) / 2
    hh, hl = np.maximum(h, np.maximum(ho, hc)), np.minimum(l, np.minimum(ho, hc))
    _, d = np_supertrend(h, l, c, 3.44, 15)
    adx = np_dmi(h, l, c, 14)[2]
    loc = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Europe/Budapest")
    m = (loc.dt.hour * 60 + loc.dt.minute).to_numpy()
    ins = (m >= 1020) & (m < 1200)
    vok = (v >= np_ema(v, 20) * 1.0) if usevol else np.ones(n, bool)
    atr_ma, atr50 = np_ema(hc, 50), np_atr(h, l, c, 50)
    hi20, lo20 = pd.Series(h).rolling(20).max().to_numpy(), pd.Series(l).rolling(20).min().to_numpy()
    # confirmed pivots (5, 5) of the HA high / low: lastSH, lastSH2, ...
    ph, pl = np.zeros(n, bool), np.zeros(n, bool)
    for i in range(10, n):
        j = i - 5
        ph[i] = hh[j] > hh[j - 5:j].max() and hh[j] > hh[j + 1:i + 1].max()
        pl[i] = hl[j] < hl[j - 5:j].min() and hl[j] < hl[j + 1:i + 1].min()
    lr_up, lr_lo = np.full(n, np.nan), np.full(n, np.nan)
    if ftype == "LinReg csatorna":
        p = np.arange(1, 101)
        for i in range(99, n):
            y = c[i - 99:i + 1][::-1]
            a, b = np.polyfit(p, y, 1)
            fit = a * p + b
            sd = np.sqrt(np.mean((y - fit) ** 2))
            lr_up[i], lr_lo[i] = fit[-1] + 2.0 * sd, fit[-1] - 2.0 * sd
    S = dict(sh=np.nan, sh2=np.nan, sl=np.nan, sl2=np.nan)
    lev = {}

    def wick_ok(k, up):
        tot = hh[k] - hl[k]
        w = (hh[k] - max(hc[k], ho[k])) if up else (min(hc[k], ho[k]) - hl[k])
        return w / tot <= wt if tot > 0 else True

    def orders(i, pos):
        if ph[i]:
            S["sh2"], S["sh"] = S["sh"], hh[i - 5]
        if pl[i]:
            S["sl2"], S["sl"] = S["sl"], hl[i - 5]
        if i < 2 or np.isnan(d[i]) or np.isnan(adx[i]):
            return []
        sbull = np.isnan(S["sl2"]) or S["sl"] > S["sl2"]
        sbear = np.isnan(S["sh2"]) or S["sh"] < S["sh2"]
        if ftype == "LinReg csatorna":
            inb = lr_lo[i] <= c[i] <= lr_up[i]
            mid = (lr_up[i] + lr_lo[i]) / 2
            bull, bear = inb and c[i] > mid, inb and c[i] < mid
        elif ftype == "ATR csatorna":
            inb = atr_ma[i] - 2 * atr50[i] <= hc[i] <= atr_ma[i] + 2 * atr50[i]
            bull, bear = inb and hc[i] > atr_ma[i], inb and hc[i] < atr_ma[i]
        elif ftype == "Donchian Channel":
            inb = lo20[i] <= hc[i] <= hi20[i]
            mid = (hi20[i] + lo20[i]) / 2
            bull, bear = inb and hc[i] > mid, inb and hc[i] < mid
        else:
            bull, bear = sbull, sbear
        tot = hh[i] - hl[i]
        body = abs(hc[i] - ho[i])
        up_w, lo_w = hh[i] - max(hc[i], ho[i]), min(hc[i], ho[i]) - hl[i]
        bp = body / tot if tot > 0 else 1.0
        doji = bp <= dm and up_w >= body * 0.3 and lo_w >= body * 0.3
        size = tot > hh[i - 1] - hl[i - 1]
        sell = hc[i - 2] >= ho[i - 2] and wick_ok(i - 2, False) and hc[i - 1] >= ho[i - 1] and wick_ok(i - 1, False) and doji and size
        buy = hc[i - 2] < ho[i - 2] and wick_ok(i - 2, True) and hc[i - 1] < ho[i - 1] and wick_ok(i - 1, True) and doji and size
        gate = adx[i] >= am and ins[i] and vok[i]
        out = []
        if buy and d[i] < 0 and gate and bull and pos == 0:
            lev[i] = (hl[i], c[i] + (c[i] - hl[i]) * 1.0)
            out.append(("entry", 1))
        if sell and d[i] > 0 and gate and bear and pos == 0:
            lev[i] = (hh[i], c[i] - (hh[i] - c[i]) * 1.0)
            out.append(("entry", -1))
        return out

    stop = lambda i, pos, ep, eb: lev[eb][0] if eb in lev else None
    tgt = lambda i, pos, ep, eb: lev[eb][1] if eb in lev else None
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt, on_close=True)
    ok, dd = compare(run_conversion(TV_ID, df, tf="15", params=params), ref)
    return ok and len(ref) > 5, f"{dd} (got {len(ref)})"


def check():
    df = bars(30000, seed=62, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    for ft in ("Swing HL", "LinReg csatorna", "ATR csatorna", "Donchian Channel"):
        ok, mm = one(df, {"Struktúra szűrő típusa": ft, "Minimum ADX": 12.0, "Doji max test %": 45.0, "Kanóc tolerancia %": 15.0, "Volume szűrő bekapcsolva": False}, ft, 0.45, 0.15, 12.0, False)
        allok &= ok
        msgs.append(mm)
    return allok, " | ".join(msgs)
