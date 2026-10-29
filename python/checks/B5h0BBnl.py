"""Independent check — Bollinger Matrix ULTRA (B5h0BBnl): 5-minute bars (24 h synthetic, price ~100, tick 0.01, pip = 10 ticks) of a stock-style symbol (60-minute periods from 09:30 New York), market orders at the next open, the script's own risk-budget quantities, pyramiding 15, commission / slippage / margin off.
Trigger: Bollinger(20, 2) sweep (previous low under the previous lower band with the close back above the band, or the plain cross when the sweep option is off), ADX(14) under the threshold, close vs the 60-minute EMA200 (lookahead off), session 02:00 - 15:30 at UTC-5. Seven grid entries while flat: level 0 at the close (market), levels 1-6 as limit orders k x step (ATR/tick/10 x 0.75, or fixed) away against the trade, quantity = budget formula x lot multiplier (7-k, inverted).
Pending orders are cancelled at the start of every bar while flat and at the end of the window; while in a position one exit order for all lots (stop SL pips from the FIRST open lot's entry price, limit at basis +/- extra pips) is re-issued every bar and a bar crossing the take-profit level (crossover on the previous bar's level) closes everything at the next open.
Uses the quantity-aware bracket reference (indep.simulate_brackets with limit entries, cancel_all, lot info), comparing quantities too. Variants: defaults; fixed 5-pip step, sweep off and HTF filter off; ADX threshold 40, 20-pip stop."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_cross_over, np_cross_under, np_dmi, np_ema, np_periods, np_security_lookahead_off, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "B5h0BBnl"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    tick = 0.01
    pip = tick * 10
    pvc = 1.0 * tick * 10
    loc = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Etc/GMT+5")
    mins = (loc.dt.hour * 60 + loc.dt.minute).to_numpy()
    sess = (mins >= 120) & (mins < 930)
    basis = np_sma(c, 20)
    dev = 2.0 * np.array([np.std(c[i - 19:i + 1]) if i >= 19 else np.nan for i in range(n)])
    up, lo = basis + dev, basis - dev
    _, _, adx = np_dmi(h, l, c, 14)
    atr = np_atr(h, l, c, 14)
    pid, last_of = np_periods(df, 60)
    ehtf = np_security_lookahead_off(np_ema(c[last_of], 200), pid, last_of)
    xdn, xup = np_cross_under(l, lo), np_cross_over(h, up)
    S = dict(prev=False, ftp=np.nan, hi1=np.nan, lo1=np.nan)

    def orders(i, info):
        out = []
        pos = info["pos"]
        step = (atr[i] / tick / 10) * 0.75 if p["atr"] else p["step"]
        with np.errstate(invalid="ignore"):
            sl_ = (l[i - 1] < lo[i - 1] and c[i] > lo[i]) if p["sweep"] and i > 0 else bool(xdn[i])
            ss_ = (h[i - 1] > up[i - 1] and c[i] < up[i]) if p["sweep"] and i > 0 else bool(xup[i])
            tl = (not p["htf"]) or c[i] > ehtf[i]
            ts = (not p["htf"]) or c[i] < ehtf[i]
            lt = sl_ and adx[i] < p["adx"] and tl and sess[i]
            st_ = ss_ and adx[i] < p["adx"] and ts and sess[i]
        tot = sum((7 - k) * max(p["sl"] - k * step, 0) for k in range(7))
        qb = 100.0 / (tot * pvc)
        if pos == 0:
            out.append(("cancel_all",))
        sess_end = (not sess[i]) and S["prev"]
        S["prev"] = bool(sess[i])
        if sess_end:
            out.append(("cancel_all",))
        ftp = basis[i] + p["extra"] * pip if pos > 0 else basis[i] - p["extra"] * pip
        with np.errstate(invalid="ignore"):
            tup = h[i] > ftp and S["hi1"] <= S["ftp"]
            tdn = l[i] < ftp and S["lo1"] >= S["ftp"]
        S.update(ftp=ftp, hi1=h[i], lo1=l[i])
        if (lt or st_) and pos == 0:
            for k in range(7):
                d = 1 if lt else -1
                price = c[i] - k * step * pip if lt else c[i] + k * step * pip
                size = qb * (7 - k)
                nm = ("buy%d" if lt else "sell%d") % k
                out.append(("entry", nm, d, size, None, None if k == 0 else price))
        if pos != 0:
            if (tup if pos > 0 else tdn):
                out.append(("close_all",))
            first = info["lots"][0]["ep"]
            stop = first - p["sl"] * pip if pos > 0 else first + p["sl"] * pip
            out.append(("exit", "X", "", None, stop, None if np.isnan(ftp) else ftp))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=15, tick=tick)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(adx=25, sl=35, step=7, atr=True, sweep=True, htf=True, extra=5.0)


def check():
    df = bars(50000, seed=691, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.1
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Step basado en ATR": False, "Step Fijo (Pips)": 5, "Confirmar Neutralización (Sweep)": False, "Filtrar por Tendencia HTF (EMA)": False}, dict(atr=False, step=5, sweep=False, htf=False)),
             ({"Filtro ADX (Solo Rangos)": 40, "Stop Loss Total (Pips)": 20}, dict(adx=40, sl=20)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
