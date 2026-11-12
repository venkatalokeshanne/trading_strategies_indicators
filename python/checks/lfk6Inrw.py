"""Independent check — Cash Account Portfolio Trend System v2 (lfk6Inrw): daily bars, market orders at the next open, slippage / commission / margin off (the per-slot share-of-equity size does not change the trade list). Long only, entries while no trade is open: close above the regime MA (SMA / EMA) that is also rising, a trigger (MACD histogram crosses zero with the MACD line positive, and / or an RSI pullback recovery: RSI recently below the dip level, crossing above the recovery level with the close above the trend-break MA), optional above-average volume and RSI-overbought veto, and the settlement / cool-down bars since the last sale. After the minimum holding period (counted from the fill bar) the position is closed at the next open when the close falls below the trailing stop (highest high since entry - ATR x multiple), the catastrophic stop (fill price - %), the trend-break MA or the regime MA, or on RSI weakness. Uses the pending-order reference broker (simulate_ord).
Variants: defaults; pullback entries with EMA regime, no volume filter and the RSI exit; high-volatility preset, either trigger, settle 3 / cool-down 2 bars, minimum hold 4; manual mode with a tight ATR multiple and hard stop."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_rsi, np_sma, run_conversion, simulate_ord

TV_ID = "lfk6Inrw"


def cu(a, b):
    pa, pb = np.r_[np.nan, a[:-1]], np.r_[np.nan, b[:-1]]
    with np.errstate(invalid="ignore"):
        return (a > b) & (pa <= pb)


def cd(a, b):
    pa, pb = np.r_[np.nan, a[:-1]], np.r_[np.nan, b[:-1]]
    with np.errstate(invalid="ignore"):
        return (a < b) & (pa >= pb)


def barssince(cond):
    out = np.full(len(cond), np.nan)
    last = None
    for i in range(len(cond)):
        if cond[i]:
            last = i
        if last is not None:
            out[i] = i - last
    return out


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    ma = (lambda x, k: np_ema(x, k)) if p["rtype"] == "EMA" else np_sma
    xma = (lambda x, k: np_ema(x, k)) if p["xtype"] == "EMA" else np_sma
    tma = ma(c, 200)
    ema_ = xma(c, p["xlen"])
    macd = np_ema(c, 12) - np_ema(c, 26)
    sig = np_ema(macd, 9)
    hist = macd - sig
    rsi = np_rsi(c, 14)
    atr = np_atr(h, l, c, 22)
    mult, hard = {"auto": (3.0, 12.0), "hv": (3.5, 18.0), "manual": (p["mult"], p["hard"])}[p["asset"]]
    with np.errstate(invalid="ignore"):
        chg = tma - np.r_[np.nan, tma[:-1]]
        volok = (v > np_sma(v, 20)) if p["usevol"] else np.ones(n, bool)
        regime = (c > tma) & (chg > 0)
        zero = np.zeros(n)
        brk = cu(hist, zero) & (macd > 0)
        bs = barssince(rsi < 40.0)
        dipped = bs <= 10
        pull = dipped & cu(rsi, np.full(n, 50.0)) & (c > ema_)
        trig = {"breakout": brk, "pullback": pull, "either": brk | pull}[p["mode"]]
        veto = rsi < 78.0
        rexit = cd(rsi, np.full(n, 40.0))
    S = dict(pp=None, lsb=None, peak=np.nan, hs=np.nan)

    def orders(i, pos, info):
        out = []
        pp, S["pp"] = S["pp"], pos
        intr = pos > 0
        if pos == 0 and pp is not None and pp > 0:
            S["lsb"] = i
        bss = 999999 if S["lsb"] is None else i - S["lsb"]
        settled = bss >= p["settle"]
        cdo = bss >= p["settle"] + p["cool"]
        held = i - info["eb"] if intr else np.nan
        holdmet = intr and held >= p["minhold"]
        if intr:
            S["peak"] = h[i] if np.isnan(S["peak"]) else max(S["peak"], h[i])
            if np.isnan(S["hs"]):
                S["hs"] = info["ep"] * (1.0 - hard / 100.0)
        else:
            S["peak"] = S["hs"] = np.nan
        with np.errstate(invalid="ignore"):
            trail = S["peak"] - mult * atr[i] if intr else np.nan
            sigl = (not intr) and regime[i] and trig[i] and volok[i] and ((not p["veto"]) or veto[i]) and settled and cdo
            ex = (intr and c[i] < trail) or (intr and p["maexit"] and c[i] < ema_[i]) or (intr and c[i] < S["hs"]) or (intr and c[i] < tma[i]) or (intr and p["rexit"] and rexit[i])
        if sigl:
            out.append(("entry", "Long", 1, None, None))
        if holdmet and ex:
            out.append(("close", "Long"))
        return out

    ref = simulate_ord(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


BASE = dict(rtype="SMA", xtype="SMA", mode="breakout", usevol=True, veto=True, rexit=False, maexit=True, asset="auto", mult=3.0, hard=12.0, settle=1, cool=0, minhold=1, xlen=50)


def check():
    df = bars(5000, seed=818)
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.6
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Entry style": "Pullback (RSI)", "Regime MA type": "EMA", "Require above-average volume": False, "Exit on RSI weakness (not recommended)": True},
              dict(mode="pullback", rtype="EMA", usevol=False, rexit=True)),
             ({"Asset class": "High-volatility stock", "Entry style": "Either (more trades)", "Settlement cooldown after a sale (bars)": 3, "Extra anti-churn cooldown (bars)": 2,
               "Minimum holding period (bars)": 4},
              dict(asset="hv", mode="either", settle=3, cool=2, minhold=4)),
             ({"Asset class": "Manual", "Trailing stop ATR multiple (Manual mode)": 1.5, "Catastrophic stop % (Manual mode)": 4.0, "Exit on close below trend-break MA": False,
               "Trend-break MA type": "EMA", "Trend-break exit MA": 30, "Veto entries when overbought": False},
              dict(asset="manual", mult=1.5, hard=4.0, maexit=False, xtype="EMA", veto=False, xlen=30)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
