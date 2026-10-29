"""Independent check — Vegas Channel Tunnel v1.1 (J6JxBgkr): hourly bars, market orders at the next open, fixed quantity 10 (the original trades 1 contract; scaled to see the scale-out pieces), commission / slippage off.
Tunnel = band of the 55 / 89 EMAs (scaled down in the variants), macro band = 576 / 676 EMAs. A close beyond the tunnel with the trigger EMA beyond it (and on the right side of the macro band when that filter is on) arms the long / short state; a later wick back into the boundary (within tol) that closes back outside it, with the trend filter still true,
triggers the entry (the regime filter blocks setups against a strong trend: ADX >= threshold and the macro EMA slope over the lookback). The stop is ATR based or the opposite tunnel edge; the first target at R x TP1 sets the script's flag (bar high / low reached it), after which the stop moves to break-even and trails by an ATR multiple (the tighter of old and new).
Exit orders are re-issued every bar from that state: scale-out share at TP1 plus the runner at the final target, or a stop-only runner in a strong trend ("ride"). Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too.
Variants: shorter EMAs 5 / 13 / 21 / 55 / 89 without the macro filter; tunnel stop, no scale-out and no trailing; regime filter on with short macro EMAs and a 1R/2R plan."""
import numpy as np

from indep import bars, compare_q, np_atr, np_dmi, np_ema, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "J6JxBgkr"
QTY = 10.0


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    e12, e144, e169, e576, e676 = (np_ema(c, p[k]) for k in ("l12", "l144", "l169", "l576", "l676"))
    tu, tl = np.fmax(e144, e169), np.fmin(e144, e169)
    mu, ml = np.fmax(e576, e676), np.fmin(e576, e676)
    atr = np_atr(h, l, c, 14)
    _, _, adx = np_dmi(h, l, c, 14)
    S = dict(ls=0, ss=0, ref=np.nan, r=np.nan, d=0, tp1=False, ride=False, stop=np.nan, flat=-100000, prev=0.0)
    sl_ = p["slook"]

    def orders(i, info):
        out = []
        pos = info["pos"]
        with np.errstate(invalid="ignore"):
            rising = e576[i] > (e576[i - sl_] if i >= sl_ else np.nan)
            strong = adx[i] >= p["adxth"]
            sup, sdn = strong and rising, strong and not rising
            alo = (not p["reg"]) or not sdn
            ash = (not p["reg"]) or not sup
            tup = (not p["mf"]) or c[i] > mu[i]
            tdn = (not p["mf"]) or c[i] < ml[i]
            bup = c[i] > tu[i] and e12[i] > tu[i]
            bdn = c[i] < tl[i] and e12[i] < tl[i]
            tol = p["tol"] * atr[i]
            lr = S["ls"] == 1 and l[i] <= tu[i] + tol and c[i] > tu[i] and tup
            sr = S["ss"] == 1 and h[i] >= tl[i] - tol and c[i] < tl[i] and tdn
            if lr:
                S["ls"] = 0
            if sr:
                S["ss"] = 0
            if S["ls"] == 1 and ((not tup) or c[i] < tu[i]):
                S["ls"] = 0
            if S["ss"] == 1 and ((not tdn) or c[i] > tl[i]):
                S["ss"] = 0
            if tup and bup:
                S["ls"] = 1
            if tdn and bdn:
                S["ss"] = 1
            if pos == 0 and S["prev"] != 0:
                S["flat"] = i
            cd = p["cool"] == 0 or i - S["flat"] >= p["cool"]
            if lr and alo and cd and pos <= 0:
                slp = c[i] - atr[i] * 2.0 if p["slm"] == "ATR" else tl[i] - atr[i] * 0.25
                risk = c[i] - slp
                if risk > 0:
                    S.update(ref=c[i], r=risk, d=1, tp1=False, stop=slp, ride=bool(p["reg"] and sup))
                    out.append(("entry", "Long", 1, QTY))
            if sr and ash and cd and pos >= 0:
                slp = c[i] + atr[i] * 2.0 if p["slm"] == "ATR" else tu[i] + atr[i] * 0.25
                risk = slp - c[i]
                if risk > 0:
                    S.update(ref=c[i], r=risk, d=-1, tp1=False, stop=slp, ride=bool(p["reg"] and sdn))
                    out.append(("entry", "Short", -1, QTY))
            partial = p["part"] and not S["ride"]
            trail = p["trail"] or S["ride"]
            if pos > 0 and S["d"] == 1:
                t1, fin = S["ref"] + p["tp1r"] * S["r"], S["ref"] + p["rr"] * S["r"]
                if h[i] >= t1:
                    S["tp1"] = True
                if p["be"] and S["tp1"]:
                    S["stop"] = max(S["stop"], S["ref"])
                if trail and S["tp1"]:
                    S["stop"] = max(S["stop"], c[i] - atr[i] * 3.0)
                if partial:
                    out += [("exit", "L Scale", "Long", 50.0, S["stop"], t1), ("exit", "L Run", "Long", None, S["stop"], fin)]
                elif S["ride"]:
                    out.append(("exit", "L Run", "Long", None, S["stop"], None))
                else:
                    out.append(("exit", "L Run", "Long", None, S["stop"], fin))
            if pos < 0 and S["d"] == -1:
                t1, fin = S["ref"] - p["tp1r"] * S["r"], S["ref"] - p["rr"] * S["r"]
                if l[i] <= t1:
                    S["tp1"] = True
                if p["be"] and S["tp1"]:
                    S["stop"] = min(S["stop"], S["ref"])
                if trail and S["tp1"]:
                    S["stop"] = min(S["stop"], c[i] + atr[i] * 3.0)
                if partial:
                    out += [("exit", "S Scale", "Short", 50.0, S["stop"], t1), ("exit", "S Run", "Short", None, S["stop"], fin)]
                elif S["ride"]:
                    out.append(("exit", "S Run", "Short", None, S["stop"], None))
                else:
                    out.append(("exit", "S Run", "Short", None, S["stop"], fin))
        S["prev"] = pos
        return out

    ref = simulate_brackets(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(l12=8, l144=55, l169=89, l576=576, l676=676, mf=True, tol=0.0, rr=3.0, slm="ATR", part=True, tp1r=1.5, be=True, trail=True, cool=0, reg=True, adxth=25.0, slook=20)


def check():
    df = bars(40000, seed=191, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    small = {"Trigger EMA": 5, "Tunnel fast EMA": 13, "Tunnel slow EMA": 21, "Macro fast EMA": 55, "Macro slow EMA": 89}
    sm = dict(l12=5, l144=13, l169=21, l576=55, l676=89)
    cases = ((dict(small), dict(sm)),
             ({**small, "Require macro trend filter": False, "Enable regime filter": False, "Stop-loss method": "Tunnel", "Scale out at TP1": False, "ATR trailing stop after TP1": False, "Retrace tolerance (ATR mult)": 0.5},
              dict(sm, mf=False, reg=False, slm="Tunnel", part=False, trail=False, tol=0.5)),
             ({**small, "Risk : Reward": 2.0, "TP1 distance (R multiple)": 1.0, "Strong-trend ADX threshold": 15.0, "Macro slope lookback": 10, "Cooldown bars after a trade closes": 3},
              dict(sm, rr=2.0, tp1r=1.0, adxth=15.0, slook=10, cool=3)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
