"""Independent check — VWAP Mean Reversion Strategy (YBqnzqDK): 5-minute bars (24 h synthetic, price ~100) of a stock-style symbol, the script's own risk-based integer quantities (equity mirrored: initial capital + closed P&L + open P&L), commission / slippage off.
Session VWAP / 1-sigma band (cumulative sums restarting at the 09:30 New York D-period change; the first period is na as in the source), 20-bar extremes, shooting-star / hammer / doji setup bars and the next bar's confirmation (engulfing or lower-high / higher-low close, outer 30 % close, size <= 1.5 ATR(10)), the previous-close-outside-the-band filter, one signal per run, the stored stop / entry / target levels, the risk-sized stop or limit entry (cancelled after 2 bars in stop mode), the exit order (stop and limit minus / plus the spread) re-issued every bar and the opposite-signal close are restated bar by bar.
Uses the quantity-aware bracket reference (indep.simulate_brackets with pending stop / limit entries). Variants: defaults (limit at the close); stop entries; engulfing only with the VWAP filters off and the fixed ATR."""
import numpy as np

from indep import bars, compare_q, np_atr, np_periods, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "YBqnzqDK"
SPREAD = 0.09


def wfn(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    pid, _ = np_periods(df, 1440)
    tp = (h + l + c) / 3
    cv, cpv, cpv2 = np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan)
    for i in range(n):
        if i > 0 and pid[i] != pid[i - 1]:
            cv[i], cpv[i], cpv2[i] = v[i], tp[i] * v[i], tp[i] * tp[i] * v[i]
        elif i > 0:
            cv[i], cpv[i], cpv2[i] = cv[i - 1] + v[i], cpv[i - 1] + tp[i] * v[i], cpv2[i - 1] + tp[i] * tp[i] * v[i]
    with np.errstate(invalid="ignore", divide="ignore"):
        vw = cpv / cv
        sd = np.sqrt(np.maximum(cpv2 / cv - vw ** 2, 0.0))
    up, lo = vw + sd, vw - sd
    atr = np_atr(h, l, c, 10)
    hh, ll = wfn(h, 20, np.max), wfn(l, 20, np.min)
    log: list = []
    S = dict(bse=0, bue=0, bc=0, bl=0, ls=np.nan, lt=np.nan, ss=np.nan, st=np.nan, lbar=None, sbar=None)

    def orders(i, info):
        out = []
        eq = 100000.0 + sum(d * (xp - ep) * q for d, _, ep, _, xp, q in log) + sum(x["d"] * x["q"] * (c[i] - x["ep"]) for x in info["lots"])
        a = atr[i]
        c1, o1, h1, l1 = (c[i - 1], o[i - 1], h[i - 1], l[i - 1]) if i else (np.nan,) * 4
        with np.errstate(invalid="ignore", divide="ignore"):
            above, below = c1 > up[i], c1 < lo[i]
            body, cd = abs(c[i] - o[i]), h[i] - l[i]
            uw, lw = h[i] - max(o[i], c[i]), min(o[i], c[i]) - l[i]
            valid = cd > 0
            atr_ok = cd <= a * 1.5
            cp = (c[i] - l[i]) / cd if valid else 0.0
            ss = valid and body <= cd * 0.3 and uw >= body * 2.0 and lw <= body
            ham = valid and body <= cd * 0.3 and lw >= body * 2.0 and uw <= body
            doji = valid and body <= cd * 0.2
            bear_setup = bool((ss or doji) and h[i] >= hh[i])
            bull_setup = bool((ham or doji) and l[i] <= ll[i])
            b_eng = c[i] < o[i] and c1 > o1 and o[i] >= c1 and c[i] <= o1
            u_eng = c[i] > o[i] and c1 < o1 and o[i] <= c1 and c[i] >= o1
            lh = h[i] < h1 and c[i] < l1
            hl = l[i] > l1 and c[i] > h1
            bear = bool(S["bse"] == 1 and cp <= 0.3 and atr_ok)
            bull = bool(S["bue"] == 1 and cp >= 0.7 and atr_ok)
            if p["eng"]:
                bear, bull = bear and b_eng, bull and u_eng
            else:
                bear, bull = bear and (b_eng or lh), bull and (u_eng or hl)
            bc_, bl_ = bull, bear
            if p["vwapf"]:
                bc_, bl_ = bc_ and bool(below), bl_ and bool(above)
            bc_, bl_ = bc_ and bool(below), bl_ and bool(above)           # mean-reversion switch (on)
        lsig = bc_ and not S["bc"] == 1
        ssig = bl_ and not S["bl"] == 1
        buf, ebuf = a * 0.01, a * 0.01
        if lsig:
            S["lbar"] = i
            S["ls"] = l[i] - buf
            ent = h[i] + buf
            risk = max(ent - S["ls"], a * 0.2)
            S["lt"] = ent + risk * 2.0
            qty = float(np.floor(eq * 0.01 / risk)) if risk > 0 else 0.0
            if qty > 0:
                if p["stop"]:
                    out.append(("entry", "Long", 1, qty, ent + SPREAD, None))
                else:
                    out.append(("entry", "Long", 1, qty, None, c[i] + ebuf + SPREAD))
        if ssig:
            S["sbar"] = i
            S["ss"] = h[i] + buf
            ent = l[i] - buf
            risk = max(S["ss"] - ent, a * 0.2)
            S["st"] = ent - risk * 2.0
            qty = float(np.floor(eq * 0.01 / risk)) if risk > 0 else 0.0
            if qty > 0:
                if p["stop"]:
                    out.append(("entry", "Short", -1, qty, ent - SPREAD, None))
                else:
                    out.append(("entry", "Short", -1, qty, None, c[i] - ebuf - SPREAD))
        if p["stop"]:
            if S["lbar"] is not None and i - S["lbar"] > 2:
                out.append(("cancel", "Long"))
                S["lbar"] = None
            if S["sbar"] is not None and i - S["sbar"] > 2:
                out.append(("cancel", "Short"))
                S["sbar"] = None
        nn = lambda x: None if np.isnan(x) else float(x)
        out.append(("exit", "Long Exit", "Long", None, nn(S["ls"] - SPREAD), nn(S["lt"] - SPREAD)))
        out.append(("exit", "Short Exit", "Short", None, nn(S["ss"] + SPREAD), nn(S["st"] + SPREAD)))
        if lsig:
            out.append(("close", "Short"))
        if ssig:
            out.append(("close", "Long"))
        S["bse"], S["bue"], S["bc"], S["bl"] = int(bear_setup), int(bull_setup), int(bc_), int(bl_)
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=0.01, qty_step=1e-9, log=log)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


def check():
    df = bars(60000, seed=5, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.2
    msgs, allok = [], True
    cases = (({}, dict(stop=False, eng=False, vwapf=True)),
             ({"Entry Type": "Stop"}, dict(stop=True, eng=False, vwapf=True)),
             ({"Engulfing Candles Only for Entries": True, "Require Price Outside 1σ": False}, dict(stop=False, eng=True, vwapf=False)))
    for params, ov in cases:
        ok, m = one(df, params, ov)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
