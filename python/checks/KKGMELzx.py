"""Independent check — SPY Wheel Strategy (KKGMELzx): 2800 daily business-day bars (09:30 New York stamps, SPY-like price ~300, no drift) of a stock-style symbol with a synthetic VIX series served through the data provider, orders at the bar's close (process_orders_on_close), 100 shares per entry, commission / slippage off.
Initial buy on the start bar, cost basis = the last open lot's entry price after each new fill, 3-close SMA(200) regime exit (close all + cancel all) and re-entry above the SMA, the covered-call assignment close (previous close's strike in normal VIX, the same bar's strike when VIX >= threshold, strike >= cost basis, close > strike), instant re-entry or the cash-secured-put limit order (gates: SMA, EMA, RSI band, VIX, VWAP, macro) are restated bar by bar.
Uses the quantity-aware bracket reference (indep.simulate_brackets with limit entries, cancel / cancel_all, on_close). Variants: defaults with an earlier start; CSP re-entry with a 20 VIX threshold; high-VIX CC (threshold 16), regime exit after 1 close."""
import math

import numpy as np
import pandas as pd

from indep import bars, compare_q, np_ema, np_rsi, np_sma, np_vwap, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "KKGMELzx"


def one(df, vix, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    vx = vix["close"].to_numpy()
    n = len(c)
    t = df["time"].to_numpy()
    sma, ema, rsi = np_sma(c, 200), np_ema(c, 20), np_rsi(c, 14)
    S = dict(prev=None, cb=np.nan, cc=np.nan, ct=0, exited=False, sb=None, cc_prev=np.nan)

    def orders(i, info):
        out = []
        pos = info["pos"]
        pp = S["prev"]
        S["prev"] = pos
        cc_prev = S["cc"]                        # cc_str_live[1] = the value at the end of the previous bar
        hold = pos >= 100
        hi = (not np.isnan(vx[i])) and vx[i] >= p["vix"]
        with np.errstate(invalid="ignore"):
            g1, g2 = c[i] > sma[i], c[i] > ema[i]
            g3 = p["rlo"] > p["rhi"] or not (rsi[i] >= p["rlo"] and rsi[i] <= p["rhi"])
            g4 = (not np.isnan(vx[i])) and vx[i] < p["vix"]
            csp_ok = bool(g1 and g2 and g3 and g4)
            S["ct"] = (S["ct"] + 1 if c[i] < sma[i] else 0) if hold else 0
        rb = hold and S["ct"] >= p["days"]
        started = t[i] >= p["start"]
        if started and i > 0 and t[i - 1] < p["start"] and pos == 0:
            out.append(("entry", "LONG", 1, 100.0))
            S["sb"] = i
        if pos >= 100 and pp is not None and pp < 100:
            if info["lots"]:
                S["cb"] = info["lots"][-1]["ep"]
        if rb and not S["exited"]:
            out += [("close_all",), ("cancel_all",)]
            S["cb"], S["cc"], S["exited"] = np.nan, np.nan, True
        reb = False
        with np.errstate(invalid="ignore"):
            if S["exited"] and not hold and c[i] > sma[i] and started:
                out.append(("entry", "LONG", 1, 100.0))
                S["exited"], reb = False, True
        if hold and (not rb) and started and not np.isnan(S["cb"]):
            pct = p['cc_vix'] if hi else p['cc']
            ns = float(math.ceil(c[i] * (1.0 + pct)))
            chk = ns if hi else cc_prev
            if (not np.isnan(chk)) and c[i] > chk and chk >= S["cb"]:
                out.append(("close_all",))
                S["cc"] = np.nan
            else:
                S["cc"] = ns if ns >= S["cb"] else np.nan
        if (not hold) and (not S["exited"]) and (not reb) and S["sb"] is not None and i > S["sb"] and started:
            if not p["csp"]:
                out.append(("entry", "LONG", 1, 100.0))
            else:
                out.append(("cancel", "LONG"))
                if csp_ok:
                    out.append(("entry", "LONG", 1, 100.0, None, float(math.floor(o[i] * (1.0 - 0.015)))))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, on_close=True, tick=0.01, qty_step=1e-9)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params, data_provider=lambda s, tf: vix,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


def check():
    df = bars(2800, seed=3, freq="B")
    df["time"] = df["time"] + int(14.5 * 3600 * 1000)
    lc = np.log(df["close"].to_numpy() / 100)
    det = lc - np.polyval(np.polyfit(np.arange(len(lc)), lc, 1), np.arange(len(lc)))
    rel = {k: df[k].to_numpy() / df["close"].to_numpy() for k in ("open", "high", "low", "close")}
    for k in rel:
        df[k] = 300 * np.exp(0.5 * det) * rel[k]
    vix = df.copy()
    sdz = (df["close"] - df["close"].mean()) / df["close"].std()
    rng = np.random.default_rng(5)
    for k in ("open", "high", "low", "close"):
        vix[k] = 20.0 - 4.0 * sdz.to_numpy() + rng.normal(0, 1.5, len(df))
    start = int(df["time"].iloc[300])
    base = dict(vix=100.0, rlo=75.0, rhi=85.0, days=3, csp=False, start=start, cc=0.0025, cc_vix=0.03)
    msgs, allok = [], True
    c1 = {"Strategy Start Date": start, "VIX Gate Threshold": 100.0, "CC Strike % OTM — Normal VIX": 0.25}
    cases = ((c1, {}),
             ({**c1, "Use CSP re-entry (uncheck = instant re-entry at open)": True, "RSI Block Zone — Low": 62.0, "RSI Block Zone — High": 72.0}, dict(csp=True, rlo=62.0, rhi=72.0)),
             ({**c1, "VIX Gate Threshold": 22.0, "200 SMA Breach Days to Exit": 2, "CC Strike % OTM — High VIX": 0.5}, dict(vix=22.0, days=2, cc_vix=0.005)))
    for params, ov in cases:
        ok, m = one(df, vix, params, {**base, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
