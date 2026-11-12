"""Independent check — TASC One Percent A Week (nVECqIQx): daily bars (business days stamped 09:30 New York) and 15-minute bars (24 h synthetic, regular session 09:30-16:00) of a stock-style symbol, fixed quantity, commission / slippage off.
Monday's first regular bar records the weekly open and (re)issues a long limit 1 % below it; after a fill the first regular bar sends a limit exit 1 % above the average price, a low under -0.5 % moves that exit to break-even (once), and a position open on Friday's last regular bar is closed immediately (at that bar's close).
Uses the quantity-aware bracket reference (indep.simulate_brackets with limit entries, limit exits and on_close for the immediate close). Variants: daily; 15-minute."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "nVECqIQx"
QTY = 10.0


def one(df, tf):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    loc = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (loc.dt.hour * 60 + loc.dt.minute).to_numpy()
    dow = loc.dt.dayofweek.to_numpy()                       # Monday = 0
    day = loc.dt.date.to_numpy()
    daily = tf == "D"
    reg = np.full(n, True) if daily else (mins >= 570) & (mins < 960)
    first = np.array([True if daily else (reg[i] and (i == 0 or not reg[i - 1] or day[i] != day[i - 1])) for i in range(n)])
    last = np.array([True if daily else (reg[i] and mins[i] + 15 >= 960) for i in range(n)])
    S = dict(w=np.nan, pt=np.nan, send=False, be=False, prev=None)

    def orders(i, info):
        out = []
        pos, avg = info["pos"], info["avg"]
        pp = S["prev"]
        S["prev"] = pos
        newsess = dow[i] == 0 and first[i]
        if newsess:
            S["w"] = o[i]
        down1 = S["w"] * 0.99
        if newsess:
            out.append(("entry", "Buy", 1, QTY, None, down1))
            S["pt"] = np.nan
        newfill = pp is not None and pos != pp
        if pos > 0 and newfill:
            S["send"], S["be"] = True, False
        if S["send"] and first[i] and not S["be"]:
            S["pt"] = avg * 1.01
            out.append(("exit", "profit", "Buy", None, None, S["pt"]))
            S["send"] = False
        with np.errstate(invalid="ignore"):
            bet = avg * 0.995
            hit = l[i] < bet
        if hit and not S["be"]:
            S["pt"] = avg
            out.append(("exit", "profit", "Buy", None, None, avg))
            S["be"] = True
        if dow[i] == 4 and pos > 0 and last[i]:
            out.append(("close_all",))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, on_close=True, tick=0.01, qty_step=1e-9)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ov = {"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf=tf, strategy_overrides=ov), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


def check():
    msgs, allok = [], True
    d = bars(6000, seed=71, freq="B")
    d["time"] = d["time"] + int(14.5 * 3600 * 1000)
    for k in ("open", "high", "low", "close"):
        d[k] = 100 * (d[k] / 100) ** 0.35
    m = bars(60000, seed=72, freq="15min")
    for k in ("open", "high", "low", "close"):
        m[k] = 100 * (m[k] / 100) ** 0.12
    for df, tf in ((d, "D"), (m, "15")):
        ok, msg = one(df, tf)
        allok &= ok
        msgs.append(msg)
    return allok, " | ".join(msgs)
