"""Independent check — Tomukas Sweep Reclaim Scale-In (IFSv46kK): hourly bars of a stock-style symbol, process_orders_on_close (orders fill at the signal close), quantities = percent of EQUITY / close with equity mirrored as initial capital + closed profit + open profit at the close (commission / slippage / margin off), pyramiding 5.
Swing highs / lows (left = right = 8 bars: left strictly, right not) are swept by a later bar beyond them by min..max ATR; a close back through the swept level by a buffer, with strong close location / body / EMA200 bias within the reclaim window, signals; stage-1 entry of 10 % of equity (closing an opposite position first), scale-ins of 10 / 20 / 40 / 80 % of equity when the low (high) reaches the step % from the first entry;
everything is closed when the high (low) reaches the take-profit % from the average price. Uses the quantity-aware bracket reference (indep.simulate_brackets, on_close, closed-piece log for the equity), comparing quantities too.
Variants: swing 4/4 with TP 0.8 %; EMA bias off, step 0.5 %, TP 1.0 %."""
import numpy as np

from indep import bars, compare_q, np_atr, np_ema, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "IFSv46kK"
CAP = 10000.0


def pivots(x, left, right, high):
    n = len(x)
    out = np.full(n, np.nan)
    for i in range(left + right, n):
        m = i - right
        c = x[m]
        lw, rw = x[m - left:m], x[m + 1:i + 1]
        ok = (np.all(c > lw) and np.all(c >= rw)) if high else (np.all(c < lw) and np.all(c <= rw))
        if ok:
            out[i] = c
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr = np_atr(h, l, c, 14)
    ema = np_ema(c, 200)
    k = p["sw"]
    ph, pl = pivots(h, k, k, True), pivots(l, k, k, False)
    tick = 0.01
    log = []
    S = dict(sh=np.nan, sl=np.nan, shb=None, slb=None, hs=False, ls=False, hsb=None, lsb=None, hsl=np.nan, lsl=np.nan, stage=0, base=np.nan, d=0, done=0, realized=0.0)
    Q = (10.0, 10.0, 20.0, 40.0, 80.0)

    def orders(i, info):
        out = []
        pos = info["pos"]
        while S["done"] < len(log):
            r = log[S["done"]]
            S["realized"] += (r[4] - r[2]) * r[5] * r[0]
            S["done"] += 1
        eq = CAP + S["realized"] + sum((c[i] - x["ep"]) * x["q"] * x["d"] for x in info["lots"])
        fq = lambda pct: eq * pct / 100.0 / c[i]
        sa = max(0.0 if np.isnan(atr[i]) else atr[i], tick)
        with np.errstate(invalid="ignore"):
            bb = (not p["ema"]) or c[i] > ema[i]
            br = (not p["ema"]) or c[i] < ema[i]
            body = abs(c[i] - o[i]) / sa
            rng = max(h[i] - l[i], tick)
            bcl, scl = (c[i] - l[i]) / rng, (h[i] - c[i]) / rng
            if not np.isnan(ph[i]):
                S.update(sh=ph[i], shb=i - k, hs=False)
            if not np.isnan(pl[i]):
                S.update(sl=pl[i], slb=i - k, ls=False)
            hd = (h[i] - S["sh"]) / sa if not np.isnan(S["sh"]) else np.nan
            ld = (S["sl"] - l[i]) / sa if not np.isnan(S["sl"]) else np.nan
            nh = (not np.isnan(S["sh"])) and not S["hs"] and i > S["shb"] and h[i] > S["sh"] and 0.05 <= hd <= 0.80
            nl = (not np.isnan(S["sl"])) and not S["ls"] and i > S["slb"] and l[i] < S["sl"] and 0.05 <= ld <= 0.80
            if nh:
                S.update(hs=True, hsb=i, hsl=S["sh"])
            if nl:
                S.update(ls=True, lsb=i, lsl=S["sl"])
            sr = S["hs"] and S["hsb"] is not None and i - S["hsb"] <= 3 and c[i] < S["hsl"] - sa * 0.02 and scl >= 0.60 and body >= 0.05 and br
            brc = S["ls"] and S["lsb"] is not None and i - S["lsb"] <= 3 and c[i] > S["lsl"] + sa * 0.02 and bcl >= 0.60 and body >= 0.05 and bb
        if sr:
            S["hs"] = False
        if brc:
            S["ls"] = False
        if sr and brc:
            sr = brc = False
        if pos == 0:
            S.update(stage=0, base=np.nan, d=0)
        if brc and (pos == 0 or pos < 0):
            if pos < 0:
                out.append(("close_all",))
            out.append(("entry", "L1", 1, fq(Q[0])))
            S.update(base=c[i], stage=1, d=1)
        if sr and (pos == 0 or pos > 0):
            if pos > 0:
                out.append(("close_all",))
            out.append(("entry", "S1", -1, fq(Q[0])))
            S.update(base=c[i], stage=1, d=-1)
        if pos > 0 and S["d"] == 1 and 0 < S["stage"] < 5:
            if l[i] <= S["base"] * (1 - p["step"] * S["stage"] / 100):
                S["stage"] += 1
                out.append(("entry", "L%d" % S["stage"], 1, fq(Q[S["stage"] - 1])))
        if pos < 0 and S["d"] == -1 and 0 < S["stage"] < 5:
            if h[i] >= S["base"] * (1 + p["step"] * S["stage"] / 100):
                S["stage"] += 1
                out.append(("entry", "S%d" % S["stage"], -1, fq(Q[S["stage"] - 1])))
        avg = info["avg"]
        if pos > 0 and h[i] >= avg * (1 + p["tp"] / 100):
            out.append(("close_all",))
        if pos < 0 and l[i] <= avg * (1 - p["tp"] / 100):
            out.append(("close_all",))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=5, on_close=True, log=log)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(sw=8, tp=0.40, step=0.30, ema=True)


def check():
    df = bars(30000, seed=681, freq="1h")
    for kk in ("open", "high", "low", "close"):
        df[kk] = 100 * (df[kk] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({"Swing Left": 4, "Swing Right": 4, "Take Profit Fixed % From Average": 0.8}, dict(sw=4, tp=0.8)),
             ({"Use EMA200 Bias": False, "Scale-In Step Fixed %": 0.5, "Take Profit Fixed % From Average": 1.0, "Swing Left": 5, "Swing Right": 5}, dict(ema=False, step=0.5, tp=1.0, sw=5)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
