"""Independent check — TRADLEWARE DCA+Trend ETF (et8U6rd3), daily bars. The 2 % hysteresis regime on SMA(200), the monthly
dollar-cost buys, the crash close, the dip-ladder rungs and the lump re-entry are replayed bar by bar against the quantity-aware
reference broker (pyramiding 500, fills at the next open). The last-bar close order never fills, so the final lots stay open."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_sma, run_conversion, simulate_brackets

TV_ID = "et8U6rd3"


def reference(df, whole=False, hyst=0.02, death=False, ladder=True):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ts = pd.to_datetime(df.time, unit="ms", utc=True)
    month = ts.dt.month.to_numpy()
    t0 = int(pd.Timestamp("2020-01-01", tz="UTC").timestamp() * 1000)
    tm = df.time.to_numpy()
    s200, s50 = np_sma(c, 200), np_sma(c, 50)
    S = dict(base=False, safe_prev=False, crash=False, lump=False, exited=0.0, fired=[False] * 3, comm=0.0, high=np.nan, bank=0.0)
    rungs = (0.15, 0.20, 0.30)

    def orders(i, info):
        out = []
        if hyst > 0:
            if c[i] > s200[i] * (1 + hyst):
                S["base"] = True
            elif c[i] < s200[i] * (1 - hyst):
                S["base"] = False
        else:
            S["base"] = bool(c[i] > s200[i])
        safe = S["base"] and (bool(s50[i] > s200[i]) if death else True)
        newm = i == 0 or month[i] != month[i - 1]
        crash_ev = (not safe) and S["safe_prev"]
        S["safe_prev"] = safe
        inw = tm[i] >= t0 and i != n - 1
        if inw:
            S["high"] = c[i] if np.isnan(S["high"]) else max(S["high"], c[i])
        if inw and info["pos"] > 0 and crash_ev:
            S["exited"] = info["pos"] * c[i]
            out.append(("close_all",))
            S.update(crash=True, lump=False, fired=[False] * 3, comm=0.0)
        if inw and ladder and S["crash"] and not S["lump"] and not safe and not crash_ev:
            per = S["exited"] * 0.95 / 3
            for k, p in enumerate(rungs):
                if not S["fired"][k] and c[i] <= S["high"] * (1 - p):
                    out.append(("entry", f"rung{k + 1}", 1, per / c[i]))
                    S["fired"][k] = True
                    S["comm"] += per
        if inw and S["crash"] and not S["lump"] and safe:
            budget = max(S["exited"] * 0.95 - S["comm"], 0.0)
            if budget > 0:
                out.append(("entry", "lump", 1, budget / c[i]))
            S["lump"] = True
        if inw and newm:
            if whole:
                avail = S["bank"] + 300.0
                sh = np.floor(avail / c[i])
                if sh >= 1:
                    out.append(("entry", "dca", 1, sh))
                    S["bank"] = avail - sh * c[i]
                else:
                    S["bank"] = avail
            else:
                out.append(("entry", "dca", 1, 300.0 / c[i]))
        if i == n - 1:
            out.append(("close_all",))
        return out

    return simulate_brackets(o, h, l, c, orders, pyramiding=500)


def check():
    df = bars(3000, seed=33, freq="D")
    msgs, ok_all = [], True
    for params, kw in (({}, {}), ({"Whole-Share DCA (bank remainder)": True}, {"whole": True}),
                       ({"Death Cross Confirmation": True, "SMA Hysteresis Band (%)": 0.0}, {"death": True, "hyst": 0.0})):
        ref = reference(df, **kw)
        res = run_conversion(TV_ID, df, tf="D", params=params,
                             strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0})
        ok, d = compare_q(res, ref)
        ok_all = ok_all and ok and len(ref) > 12
        msgs.append(f"{d} (got {len(ref)})")
    return ok_all, " | ".join(msgs)
