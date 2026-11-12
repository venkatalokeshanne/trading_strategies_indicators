"""Independent check — Cluster Breakout Strategy v8 (DkDNMQsn): 5-minute bars on an Asia/Kolkata chart (session 09:15-15:30, 24 h synthetic data), process_orders_on_close, 2 units per trade. Cluster = the 10-bar range <= 2 x ATR14 with ATR14 below its value 20 bars ago; the box (high / low of the latest changed cluster) stays active; a close above box top + 0.1 ATR (from at-or-below the previous bar's top + buffer) with a close in the top 40 % of the bar, volume above 1.3 x SMA20(volume), inside the session, under 3 entries a trading day and outside the 5-bar cooldown after an exit, enters at the close. Levels (percent of the signal close): stop 0.5 %, first target 1 %, second target 2 %, break-even stop at +0.5 %. Each bar in the trade (script time): bars += 1; the first close beyond the first target closes 1 unit at the close; the exit (stop / limit by phase) is issued (working from the next bar); bars >= 20 closes the rest (a close of the same id replaces a pending partial close). Outside the session any position is closed. Uses the pending-order reference broker (simulate_ord, on_close, with partial closes). Commission / slippage off on the pinelib side.
Variants: defaults; 6-bar cluster with 4 ATR tightness, no contraction, no volume confirmation, 1 % stop and first target 0.4 %."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_sma, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "DkDNMQsn"


def one(df, params, clen, tight, contr, volc, slp, tp1p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    ist = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Asia/Kolkata")
    m = (ist.dt.hour * 60 + ist.dt.minute).to_numpy()
    day = (ist.dt.tz_localize(None) - pd.Timedelta(minutes=555)).dt.date.to_numpy()
    ins = (m >= 555) & (m < 930)
    atr = np_atr(h, l, c, 14)
    chi = np.array([h[max(0, i - clen + 1):i + 1].max() if i >= clen - 1 else np.nan for i in range(n)])
    clo = np.array([l[max(0, i - clen + 1):i + 1].min() if i >= clen - 1 else np.nan for i in range(n)])
    vsma = np_sma(v, 20)
    S = dict(bt=np.nan, bb=np.nan, act=False, td=0, le=-1, pp=0, btp=np.nan, bbp=np.nan, bufp=np.nan, tp1=np.nan, tp2=np.nan, fsl=np.nan, besl=np.nan, bit=0, ph2=False)

    def orders(i, pos):
        out = []
        pp = S["pp"]
        S["pp"] = pos
        with np.errstate(invalid="ignore"):
            tightok = (chi[i] - clo[i]) <= atr[i] * tight
            contok = (not contr) or (atr[i] < atr[i - 20] if i >= 20 else False)
            cluster = tightok and contok
            volok = (not volc) or (v[i] > vsma[i] * 1.3)
        bt1, bb1, bu1 = S["bt"], S["bb"], S["bufp"]
        if cluster and (S["bt"] != chi[i] or S["bb"] != clo[i] or not S["act"]):
            S["bt"], S["bb"], S["act"] = chi[i], clo[i], True
        if i > 0 and day[i] != day[i - 1]:
            S["td"] = 0
        cool = S["le"] >= 0 and (i - S["le"]) < 5
        rg = h[i] - l[i]
        cp = (c[i] - l[i]) / rg if rg > 0 else 0.5
        buf = atr[i] * 0.1
        with np.errstate(invalid="ignore"):
            lb = S["act"] and c[i] > S["bt"] + buf and c[i - 1] <= bt1 + bu1
            sb = S["act"] and c[i] < S["bb"] - buf and c[i - 1] >= bb1 - bu1
            can = ins[i] and S["td"] < 3 and not cool
            ls = lb and can and volok and cp >= 0.6
            ss = sb and can and volok and cp <= 0.4
        S["bufp"] = buf
        if ls and pos == 0:
            out.append(("entry", "Long", 1, None, None, 2))
            S.update(bit=0, ph2=False, fsl=c[i] * (1 - slp / 100), tp1=c[i] * (1 + tp1p / 100), tp2=c[i] * (1 + tp1p * 2.0 / 100), besl=c[i] * 1.005)
            S["td"] += 1
        if ss and pos == 0:
            out.append(("entry", "Short", -1, None, None, 2))
            S.update(bit=0, ph2=False, fsl=c[i] * (1 + slp / 100), tp1=c[i] * (1 - tp1p / 100), tp2=c[i] * (1 - tp1p * 2.0 / 100), besl=c[i] * 0.995)
            S["td"] += 1
        for d, name, xname in ((1, "Long", "Long-exit"), (-1, "Short", "Short-exit")):
            if (pos > 0) if d > 0 else (pos < 0):
                S["bit"] += 1
                hit = (c[i] >= S["tp1"]) if d > 0 else (c[i] <= S["tp1"])
                if not S["ph2"] and hit:
                    out.append(("close_part", name, 1))
                    S["ph2"] = True
                out.append(("exit", xname, name, S["besl"] if S["ph2"] else S["fsl"], S["tp2"] if S["ph2"] else S["tp1"]))
                if S["bit"] >= 20:
                    out = [a for a in out if not (a[0] == "close_part" and a[1] == name)]       # same-id close replaces the pending partial
                    out.append(("close", name))
        if not ins[i] and pos != 0:
            out.append(("close_all",))
        if pos == 0 and pp != 0:
            S["le"] = i
        if pos == 0:
            S.update(tp1=np.nan, tp2=np.nan, fsl=np.nan, besl=np.nan, bit=0, ph2=False)
        return out

    ref = simulate_ord(o, h, l, c, orders, on_close=True)
    sym = SymbolInfo.make("NSE:NIFTY", "stock", qty_step=1e-9, timezone="Asia/Kolkata", session="0915-1530")
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides={"slippage": 0, "commission_value": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(40000, seed=818, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 20000 * (df[k] / 100) ** 0.12
    msgs, allok = [], True
    cases = (({}, (10, 2.0, True, True, 0.5, 1.0)),
             ({"Cluster lookback (bars)": 6, "Cluster tightness (range <= ATR x)": 4.0, "Require volatility to be contracting": False, "Confirm with volume (auto-off if none)": False,
               "Initial stop-loss %": 1.0, "First target % (50% closed here)": 0.4}, (6, 4.0, False, False, 1.0, 0.4)))
    for params, args in cases:
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
