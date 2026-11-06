"""Independent check — RKLB 5m ORB I3 VWAP Long (Wl9QUzkZ): 5-minute bars (24 h synthetic, compressed) on a US stock chart (trading day from 09:30 New York), pending stop entries, market close at the next open. The first bar of the regular session (09:30) fixes the opening range with its own high / low (ready from the next regular bar on); range % = (high - low) / mid x 100 must be inside [0.3, 6]. Entry window 09:35-15:30: a buy-stop at the opening high + 1 tick (a sell-stop at the low - 1 tick for the short side) is renewed every bar while flat and no trade has been taken today, with the VWAP (hlc3, reset on the trading day) side filter and the optional pullback-into-range requirement. Once in the position: today's trading is over, the opposite pending order is cancelled and the exit is issued (stop = the other side of the range, target = entry stop +/- reward/risk x risk) so it works from the next bar; pending orders are cancelled outside the entry window and after a trade; in the 15:55 bar or outside the regular session they are cancelled and the position is closed. Uses the pending-order reference broker (simulate_ord). Margin / slippage / commission off on the pinelib side.
Variants: long only (default); both sides with the retest requirement and VWAP filter off, reward/risk 1.5."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "Wl9QUzkZ"


def one(df, params, sides, rr, vwapf, retest):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    day = (ny.dt.tz_localize(None) - pd.Timedelta(minutes=570)).dt.date.to_numpy()
    hl3 = (h + l + c) / 3
    vw = np.zeros(n)
    pv = vv = 0.0
    for i in range(n):
        if i == 0 or day[i] != day[i - 1]:
            pv = vv = 0.0
        pv += hl3[i] * v[i]
        vv += v[i]
        vw[i] = pv / vv
    inreg = (m >= 570) & (m < 960)
    inent = (m >= 575) & (m < 930)
    inflat = (m >= 955) & (m < 960)
    S = dict(oh=np.nan, ol=np.nan, om=np.nan, ready=False, traded=False, pbl=False, pbs=False, ob=-1)

    def orders(i, pos):
        out = []
        newreg = inreg[i] and (i == 0 or day[i] != day[i - 1])
        if newreg:
            S.update(oh=h[i], ol=l[i], om=np.nan, ready=False, traded=False, pbl=False, pbs=False, ob=i)
        if inreg[i] and not S["ready"] and S["ob"] >= 0 and i > S["ob"]:
            S["om"] = (S["oh"] + S["ol"]) / 2
            S["ready"] = True
        if S["ready"] and inent[i]:
            S["pbl"] = S["pbl"] or l[i] <= S["oh"]
            S["pbs"] = S["pbs"] or h[i] >= S["ol"]
        rdy = S["ready"]
        rp = (S["oh"] - S["ol"]) / S["om"] * 100 if rdy else np.nan
        rok = rdy and 0.3 <= rp <= 6.0
        lsp, ssp = (S["ol"], S["oh"]) if rdy else (np.nan, np.nan)
        les = S["oh"] + 0.01 if rdy else np.nan
        ses = S["ol"] - 0.01 if rdy else np.nan
        lr, sr = les - lsp, ssp - ses
        lt, stg = les + lr * rr, ses - sr * rr
        can = rok and inent[i] and not S["traded"] and pos == 0
        if can and sides in ("both", "long") and lr > 0.01 and (not vwapf or c[i] > vw[i]) and (not retest or S["pbl"]):
            out.append(("entry", "ORB Long", 1, les, None))
        if can and sides in ("both", "short") and sr > 0.01 and (not vwapf or c[i] < vw[i]) and (not retest or S["pbs"]):
            out.append(("entry", "ORB Short", -1, ses, None))
        if pos > 0:
            S["traded"] = True
            out += [("cancel", "ORB Short"), ("exit", "Long exit", "ORB Long", lsp, lt)]
        if pos < 0:
            S["traded"] = True
            out += [("cancel", "ORB Long"), ("exit", "Short exit", "ORB Short", ssp, stg)]
        if (not inent[i]) or S["traded"]:
            out += [("cancel", "ORB Long"), ("cancel", "ORB Short")]
        if inflat[i] or not inreg[i]:
            out += [("cancel", "ORB Long"), ("cancel", "ORB Short"), ("close_all",)]
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate_ord(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:RKLB", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides={"slippage": 0, "commission_value": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(30000, seed=77, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 50 * (df[k] / 100) ** 0.4
    msgs, allok = [], True
    cases = (({}, ("long", 2.0, True, False)),
             ({"Trade side": "Both", "Reward/Risk I3": 1.5, "Use VWAP direction filter": False, "Require pullback into range before breakout": True}, ("both", 1.5, False, True)))
    for params, args in cases:
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
