"""Independent check — FCPO God Mode v5 (kCDrDJDl): 5-minute bars (24 h synthetic, compressed to a ~4000 price with a 1.0 tick) on a Kuala Lumpur chart (trading day from 10:00 local), market orders at the next open. Signal = a bar in the morning (10:30-12:30) or noon (14:30-17:00) session on an allowed weekday, outside the whipsaw / EOD / Friday-PM zones, with ATR (SMA of the true range, na on the first bar) between floor and limit (ticks), body ticks and body / range ratio above the minimum, candle direction = trade direction; the daily trade counter (closed + open trades, reset by the daily time change), the monthly tick lock (profit target, optional loss limit; per calendar month) and a one-day pause after two losing trades (time + 24 h) gate it. A TP / SL in ticks from the entry price is issued while a position is open (stale levels are kept after a reversal), a time exit after N bars from the flat-to-open transition, and session-end handling (close_all at 16:55 / 12:25 / at the end of the session windows). The tick result of a closed trade comes from the last closed trade with the direction recorded at the last flat-to-open transition. Uses the pending-order reference broker (simulate_ord).
Variants: preset C defaults; custom preset with relaxed filters; short only with the baseline session-end, no daily limit and a tight time exit; monthly cap and loss limit with exits at 12:30."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_sma, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "kCDrDJDl"
PRESETS = {"C": (22, 60, 11, 0.75), "A": (12, 35, 12, 0.75)}


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sym = SymbolInfo.make("MYX:FCPO1!", "stock", timezone="Asia/Kuala_Lumpur", session="1000-1700", mintick=1.0, qty_step=1e-9)
    tick = sym.mintick
    kl = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Asia/Kuala_Lumpur")
    m = (kl.dt.hour * 60 + kl.dt.minute).to_numpy()
    hr, mi = kl.dt.hour.to_numpy(), kl.dt.minute.to_numpy()
    dow = ((kl.dt.dayofweek + 1) % 7 + 1).to_numpy()          # Pine: Sunday = 1
    month = kl.dt.month.to_numpy()
    day = (kl.dt.tz_localize(None) - pd.Timedelta(minutes=600)).dt.date.to_numpy()
    tms = df["time"].to_numpy()
    inm = (m >= 630) & (m < 750)
    inn = (m >= 870) & (m < 1020)
    c1 = np.r_[np.nan, c[:-1]]
    with np.errstate(invalid="ignore"):
        trv = np.fmax(h - l, np.fmax(np.abs(h - c1), np.abs(l - c1)))
        trv[0] = np.nan
    atr = np_sma(trv, 14)
    atrt = atr / tick
    body = np.abs(c - o)
    bt = body / tick
    rng = h - l
    br = np.where(rng > 0, body / np.where(rng > 0, rng, 1.0), 0.0)
    tp_t, sl_t, bt_min, br_min = p["preset"] if p["preset"] else (p["tp"], p["sl"], p["bticks"], p["bratio"])
    S = dict(pp=None, ltc=0, td=0, mp=0.0, curm=None, cl=0, pu=0, md=0, mep=np.nan, etp=np.nan, esl=np.nan, eb=None)
    trades: list = []
    nn = lambda x: None if np.isnan(x) else x

    def orders(i, pos, info):
        out = []
        pp, S["pp"] = S["pp"], pos
        pp0 = pp is not None and pp == 0
        ppnz = pp is not None and pp != 0
        dayok = ((dow[i] == 2 and p["dmon"]) or (dow[i] == 3) or (dow[i] == 4) or (dow[i] == 5) or (dow[i] == 6 and p["dfri"]))
        isfri = dow[i] == 6 and p["dfri"]
        whip = 930 <= m[i] < 960
        eod = 990 <= m[i] < 1020
        fripm = isfri and 960 <= m[i] < 1020
        excl = (p["xw"] and whip) or (p["xe"] and eod) or (p["xf"] and fripm)
        if i == 0:
            S["ltc"] = len(trades) + (1 if pos != 0 else 0)
        if i > 0 and day[i] != day[i - 1]:
            S["td"] = 0
        cnt = len(trades) + (1 if pos != 0 else 0)
        if cnt > S["ltc"]:
            S["td"] += 1
            S["ltc"] = cnt
        if pp0 and pos != 0:
            S["mep"] = info["ep"]
            S["md"] = 1 if pos > 0 else -1
        if i == 0 or month[i] != month[i - 1] or S["curm"] is None:
            S["mp"] = 0.0
            S["curm"] = month[i]
        if ppnz and pos == 0:
            lt = trades[-1]
            lastt = (lt[4] - lt[2]) / tick if S["md"] == 1 else (lt[2] - lt[4]) / tick
            S["mp"] += lastt
            if lastt < 0:
                S["cl"] += 1
            else:
                S["cl"] = 0
            if S["cl"] >= 2:
                S["pu"] = tms[i] + 24 * 3600 * 1000
                S["cl"] = 0
        cap = p["monthly"] and S["mp"] >= p["mmax"]
        lhit = p["mloss"] and S["mp"] <= p["mmin"]
        paused = tms[i] < S["pu"]
        dlok = p["dir"] in ("Both", "Long Only")
        dsok = p["dir"] in ("Both", "Short Only")
        dailyok = (not p["daily"]) or S["td"] < p["maxday"]
        setup = (inm[i] or inn[i]) and dayok and not paused and not excl and not cap and not lhit and dailyok
        with np.errstate(invalid="ignore"):
            vol = atrt[i] <= p["alim"] and atrt[i] >= p["aflr"]
            mom = br[i] >= br_min and bt[i] >= bt_min
        if setup and vol and mom and c[i] > o[i] and dlok:
            out.append(("entry", "Long", 1, None, None))
        if setup and vol and mom and c[i] < o[i] and dsok:
            out.append(("entry", "Short", -1, None, None))
        if pos == 0:
            S["etp"] = S["esl"] = np.nan
            S["eb"] = None
        if pp0 and pos != 0:
            S["eb"] = i
            ep = info["ep"]
            if pos > 0:
                S["etp"], S["esl"] = ep + tp_t * tick, ep - sl_t * tick
            else:
                S["etp"], S["esl"] = ep - tp_t * tick, ep + sl_t * tick
        if pos > 0:
            out.append(("exit", "Exit Long", "Long", nn(S["esl"]), nn(S["etp"])))
        if pos < 0:
            out.append(("exit", "Exit Short", "Short", nn(S["esl"]), nn(S["etp"])))
        if p["texit"] and pos != 0 and S["eb"] is not None and i - S["eb"] >= p["tbars"]:
            out.append(("close_all",))
        if p["sexit"] == "baseline":
            pm = i > 0 and inm[i - 1] and not inm[i]
            pn = i > 0 and inn[i - 1] and not inn[i]
            se = pm or pn
        elif p["sexit"] == "sharp":
            se = (hr[i] == 12 and mi[i] == 25) or (hr[i] == 16 and mi[i] == 55)
        else:
            se = hr[i] == 16 and mi[i] == 55
        if se and pos != 0:
            out.append(("close_all",))
        return out

    ref = simulate_ord(o, h, l, c, orders, log=trades)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides={"commission_value": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(preset=PRESETS["C"], tp=12, sl=30, bticks=12, bratio=0.75, alim=12.0, aflr=5.0, texit=True, tbars=15, daily=True, maxday=1, sexit="carry", dir="Both",
            dmon=True, dfri=True, xw=True, xe=True, xf=True, monthly=True, mmax=100, mloss=False, mmin=-120)


def check():
    df = bars(50000, seed=1337, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 4000 * (df[k] / 100) ** 0.1
    msgs, allok = [], True
    cases = (({}, {}),
             ({"God Mode Preset": "Custom (Use Manual Inputs)", "Manual Take Profit (Ticks)": 15, "Manual Stop Loss (Ticks)": 25, "Minimum Body Size (Ticks)": 6, "Min Body-to-Range Ratio": 0.5,
               "ATR Limit (Ticks)": 20.0, "ATR Floor (Ticks)": 3.0, "Max Trades Per Day": 2},
              dict(preset=None, tp=15, sl=25, bticks=6, bratio=0.5, alim=20.0, aflr=3.0, maxday=2)),
             ({"God Mode Preset": "Setup A (SL 35) - M15 Baseline", "Allow Trade Direction": "Short Only", "Session Exit Handling": "TradingView Buggy Baseline", "Enable Daily Trade Limit": False,
               "Time Exit Bars": 4, "ATR Limit (Ticks)": 20.0, "ATR Floor (Ticks)": 3.0, "Trade Monday": False, "Min Body-to-Range Ratio": 0.5},
              dict(preset=PRESETS["A"], bratio=0.5, dir="Short Only", sexit="baseline", daily=False, tbars=4, alim=20.0, aflr=3.0, dmon=False)),
             ({"God Mode Preset": "Custom (Use Manual Inputs)", "Manual Take Profit (Ticks)": 10, "Manual Stop Loss (Ticks)": 40, "Minimum Body Size (Ticks)": 5, "Min Body-to-Range Ratio": 0.4,
               "ATR Limit (Ticks)": 25.0, "ATR Floor (Ticks)": 2.0, "Enable Daily Trade Limit": False, "Monthly Profit Target (Ticks)": 30, "Enable Monthly Loss Limit": True,
               "Monthly Loss Limit (Ticks)": -40, "Session Exit Handling": "Exit at 12:30 Sharp", "Exclude Friday PM Whipsaw (16:00-17:00)": False},
              dict(preset=None, tp=10, sl=40, bticks=5, bratio=0.4, alim=25.0, aflr=2.0, daily=False, mmax=30, mloss=True, mmin=-40, sexit="sharp", xf=False)))
    for params, ov in cases:
        ok, mm = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(mm)
    return allok, " | ".join(msgs)
