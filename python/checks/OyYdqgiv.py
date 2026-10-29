"""Independent check — Flowrise BOT 2.0 (OyYdqgiv): hourly bars of a 24 h market (UTC), market orders at the next open (position size follows equity but does not change the trade list). Supertrend on hl2 (ATR = Wilder RMA of the true range, or the SMA of the true range): bands ratchet when the previous close was beyond the previous band, the trend flips when the close crosses the opposite previous band; a flip in the direction of the MA-200 (hl2) trend on an allowed weekday / month / hour opens a position. close_all runs on every trend change and, with the fixed take-profit option, when the close reaches the stored target (set when the signal fires while flat, cleared on the first flat bar after a trade). Uses the pending-order reference broker (simulate_ord).
Variants: defaults; fixed take-profit R:R 1 with buys only; Saturday allowed, session 10 AM - 3 PM, March / June off, SMA-ATR and multiplier 2."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_sma, np_tr, run_conversion, simulate_ord

TV_ID = "OyYdqgiv"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    tick = 0.01
    dt = pd.to_datetime(df["time"], unit="ms", utc=True)
    hr = dt.dt.hour.to_numpy()
    dow = ((dt.dt.dayofweek + 1) % 7 + 1).to_numpy()
    mon = dt.dt.month.to_numpy()
    hl2 = (h + l) / 2
    atr = np_atr(h, l, c, 10) if p["chg"] else np_sma(np_tr(h, l, c, True), 10)
    up = np.zeros(n)
    dn = np.zeros(n)
    trend = np.ones(n, int)
    for i in range(n):
        u = hl2[i] - p["mult"] * atr[i]
        d = hl2[i] + p["mult"] * atr[i]
        u1 = up[i - 1] if i and not np.isnan(up[i - 1]) else u
        d1 = dn[i - 1] if i and not np.isnan(dn[i - 1]) else d
        c1 = c[i - 1] if i else np.nan
        if c1 > u1:
            u = max(u, u1)
        if c1 < d1:
            d = min(d, d1)
        up[i], dn[i] = u, d
        t = trend[i - 1] if i else 1
        if t == -1 and c[i] > d1:
            t = 1
        elif t == 1 and c[i] < u1:
            t = -1
        trend[i] = t
    ma = np_sma(hl2, 200)
    mtr = np.where(c > ma, 1, -1)
    s24, e24 = p["sess"]
    insess = (hr >= s24) & (hr < e24) if s24 <= e24 else (hr >= s24) | (hr < e24)
    dayok = np.isin(dow, p["days"])
    monok = ~np.isin(mon, p["moff"])
    sok = insess if p["usesess"] else np.ones(n, bool)
    tp_ = np.r_[1, trend[:-1]]
    buy = (mtr == 1) & (trend == 1) & (tp_ == -1) & sok & dayok & monok
    sell = (mtr == -1) & (trend == -1) & (tp_ == 1) & sok & dayok & monok
    buy[0] = sell[0] = False
    S = dict(pp=None, tp=np.nan)

    def orders(i, pos):
        out = []
        pp, S["pp"] = S["pp"], pos
        if buy[i] and pos == 0:
            S["tp"] = c[i] + max(c[i] - up[i], tick) * p["rr"] if p["usetp"] else np.nan
        if sell[i] and pos == 0:
            S["tp"] = c[i] - max(dn[i] - c[i], tick) * p["rr"] if p["usetp"] else np.nan
        if pos == 0 and pp is not None and pp != 0:
            S["tp"] = np.nan
        tpl = p["usetp"] and pos > 0 and not np.isnan(S["tp"]) and c[i] >= S["tp"]
        tps = p["usetp"] and pos < 0 and not np.isnan(S["tp"]) and c[i] <= S["tp"]
        ex = (i > 0 and trend[i] != trend[i - 1]) or tpl or tps
        if p["type"] in ("Buy Only", "Both") and buy[i]:
            out.append(("entry", "Buy", 1, None, None))
        if p["type"] in ("Sell Only", "Both") and sell[i]:
            out.append(("entry", "Sell", -1, None, None))
        if ex:
            out.append(("close_all",))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate_ord(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, tf="60", params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(mult=3.0, chg=True, usesess=False, sess=(9, 17), days=[2, 3, 4, 5, 6], moff=[], usetp=False, rr=2.0, type="Both")


def check():
    df = bars(8000, seed=909, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({}, {}),
             ({"TP fixe (R:R) actif": True, "TP R:R": 1.0, "Type de Trade": "Buy Only"}, dict(usetp=True, rr=1.0, type="Buy Only")),
             ({"Samedi": True, "Filtre session actif": True, "Début": 10, "→ Fin": 3, "Mar": False, "Jun": False, "Change ATR Calculation Method?": False, "ATR Multiplier": 2.0},
              dict(days=[2, 3, 4, 5, 6, 7], usesess=True, sess=(10, 15), moff=[3, 6], chg=False, mult=2.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
