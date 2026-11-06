"""Independent check — Real Strength Scalper [5m] (iCRFM0LS): 5-minute bars (24 h synthetic) of a stock-style symbol, process_orders_on_close (orders fill at the signal close), fixed quantity 10 on the pinelib side (the original sizes 3 % of equity), commission / slippage / margin off.
Strength = EMA(smooth) of ROC x max(volume ratio, 0.3) x max(ADX/20, 0.3). Long: strength over the threshold and rising, ADX >= min, volume ratio >= min, +DI > -DI, SMA30 > SMA60 (shorts mirrored). Lock after a stop-out (flat after being in a position), released when strength crosses back through zero. The script's peak / entry-bar variables, the after-minimum-hold exits (flip with the SMA trend, peak drop against it)
and the per-bar re-issued percent stop are restated statement by statement. Uses the quantity-aware bracket reference (indep.simulate_brackets, on_close), comparing quantities too.
Variants: defaults with ADX/volume filters relaxed (min ADX 5, volume ratio 0.5, threshold 0.3); trend filter off with a 0.5 % stop and 15 % peak drop."""
import numpy as np

from indep import bars, compare_q, np_dmi, np_ema, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "iCRFM0LS"
QTY = 10.0


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    mom = np.r_[np.full(9, np.nan), 100 * (c[9:] - c[:-9]) / c[:-9]]
    vr = v / np_sma(v, 20)
    pdi, mdi, adx = np_dmi(h, l, c, 14)
    raw = mom * np.maximum(vr, 0.3) * np.maximum(adx / 20.0, 0.3)
    stg = np_ema(raw, 8)
    s1 = np.r_[np.nan, stg[:-1]]
    fm, sm = np_sma(c, 30), np_sma(c, 60)
    S = dict(lp=np.nan, sp=np.nan, eb=None, ll=False, sl_=False, prev=0.0)

    def orders(i, info):
        out = []
        pos, avg = info["pos"], info["avg"]
        with np.errstate(invalid="ignore"):
            up, dn = fm[i] > sm[i], fm[i] < sm[i]
            lsig = stg[i] > p["thr"] and adx[i] >= p["amin"] and vr[i] >= p["vmin"] and pdi[i] > mdi[i] and stg[i] > s1[i] and ((not p["ut"]) or up)
            ssig = stg[i] < -p["thr"] and adx[i] >= p["amin"] and vr[i] >= p["vmin"] and mdi[i] > pdi[i] and stg[i] < s1[i] and ((not p["ut"]) or dn)
            if pos > 0 and S["prev"] <= 0:
                S["lp"], S["eb"] = stg[i], i
            if pos < 0 and S["prev"] >= 0:
                S["sp"], S["eb"] = stg[i], i
            if pos > 0:
                S["lp"] = max(stg[i] if np.isnan(S["lp"]) else S["lp"], stg[i])
            if pos < 0:
                S["sp"] = min(stg[i] if np.isnan(S["sp"]) else S["sp"], stg[i])
            held = 0 if S["eb"] is None else i - S["eb"]
            lpk = S["lp"] > 0 and stg[i] < S["lp"] * (1 - p["pd"] / 100) and held >= 3
            spk = S["sp"] < 0 and stg[i] > S["sp"] * (1 - p["pd"] / 100) and held >= 3
            lfl = stg[i] <= -0.8 and held >= 3
            sfl = stg[i] >= 0.8 and held >= 3
            lx = pos > 0 and not np.isnan(S["lp"]) and (lfl if up else lpk)
            sx = pos < 0 and not np.isnan(S["sp"]) and (sfl if dn else spk)
            if S["prev"] > 0 and pos == 0:
                S["ll"] = True
            if S["prev"] < 0 and pos == 0:
                S["sl_"] = True
            if S["ll"] and stg[i] <= 0:
                S["ll"] = False
            if S["sl_"] and stg[i] >= 0:
                S["sl_"] = False
        if lsig and pos <= 0 and not S["ll"]:
            out.append(("entry", "L", 1, QTY))
        if ssig and pos >= 0 and not S["sl_"]:
            out.append(("entry", "S", -1, QTY))
        if pos > 0:
            out.append(("exit", "L-SL", "L", None, avg * (1 - p["sl"] / 100), None))
            if lx:
                out.append(("close", "L"))
                S["ll"] = False
        else:
            S["lp"] = np.nan
        if pos < 0:
            out.append(("exit", "S-SL", "S", None, avg * (1 + p["sl"] / 100), None))
            if sx:
                out.append(("close", "S"))
                S["sl_"] = False
        else:
            S["sp"] = np.nan
        S["prev"] = pos
        return out

    ref = simulate_brackets(o, h, l, c, orders, on_close=True)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(thr=1.0, amin=14.0, vmin=1.2, ut=True, sl=1.0, pd=25.0)


def check():
    df = bars(30000, seed=401, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    cases = (({"Min ADX": 5.0, "Min Volume Ratio": 0.5, "Strength threshold": 0.3}, dict(amin=5.0, vmin=0.5, thr=0.3)),
             ({"Min ADX": 5.0, "Min Volume Ratio": 0.5, "Strength threshold": 0.3, "Use SMA Trend Filter": False, "Stop Loss %": 0.5, "Peak drop % to exit": 15.0},
              dict(amin=5.0, vmin=0.5, thr=0.3, ut=False, sl=0.5, pd=15.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
