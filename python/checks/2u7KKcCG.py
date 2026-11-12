"""Independent check — Trendline Break Pro (2u7KKcCG), daily bars, market entries at the next open, fixed 10 units, commission /
slippage 0. Pivot highs / lows (5 bars each side) are rebuilt as window extremes; the descending-high / ascending-low trendlines, the
"already pierced" test over the confirmation window, the freshness limit, the 0.1 ATR break buffer and the smoothed-AO turn are
recomputed in numpy; the stop / limit / break-even / ATR-trail bookkeeping is replayed against the quantity-aware reference broker
(entry reversals, partial 50 % limit exit with a separate rest-stop order). Variants: swing stop, partial TP, no reversal."""
import numpy as np

from indep import bars, compare_q, np_atr, np_ema, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "2u7KKcCG"
QTY = 10.0


def roll(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


def reference(df, stop_mode="ATR", tp_pct=100.0, reverse=True, use_mom=True, use_tp=True):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr = np_atr(h, l, c, 14)
    hl2 = (h + l) / 2
    ao = np_ema(np_sma(hl2, 5) - np_ema(hl2, 34), 5)
    swl, swh = roll(l, 10, np.min), roll(h, 10, np.max)
    P = 5
    S = dict(a=None, b=None, rv=False, rb=False, rs=np.nan, c=None, d=None, sv=False, sb=False, ss=np.nan,
             risk=np.nan, stop=np.nan, tp=np.nan, be=False, tr=False, pl=False, ps=False)

    def orders(i, info):
        out = []
        pos, avg = info["pos"], info["avg"]
        if i >= 2 * P:
            j = i - P
            w = h[j - P:j + P + 1]
            if h[j] == w.max() and (w == h[j]).sum() == 1:
                S["a"], S["b"] = S["b"], (j, h[j])
                a, b = S["a"], S["b"]
                S["rv"] = a is not None and b[1] < a[1] and (b[0] - a[0]) >= 8
                S["rb"] = False
                if S["rv"]:
                    S["rs"] = (b[1] - a[1]) / (b[0] - a[0])
                    S["rb"] = any(c[i - k] > b[1] + S["rs"] * ((i - k) - b[0]) for k in range(P + 1))
            w = l[j - P:j + P + 1]
            if l[j] == w.min() and (w == l[j]).sum() == 1:
                S["c"], S["d"] = S["d"], (j, l[j])
                a, b = S["c"], S["d"]
                S["sv"] = a is not None and b[1] > a[1] and (b[0] - a[0]) >= 8
                S["sb"] = False
                if S["sv"]:
                    S["ss"] = (b[1] - a[1]) / (b[0] - a[0])
                    S["sb"] = any(c[i - k] < b[1] + S["ss"] * ((i - k) - b[0]) for k in range(P + 1))
        res_lv = S["b"][1] + S["rs"] * (i - S["b"][0]) if S["rv"] else np.nan
        sup_lv = S["d"][1] + S["ss"] * (i - S["d"][0]) if S["sv"] else np.nan
        rf = S["b"] is not None and i - S["b"][0] <= 150
        sf = S["d"] is not None and i - S["d"][0] <= 150
        up = S["rv"] and not S["rb"] and rf and c[i] > res_lv + atr[i] * 0.10
        dn = S["sv"] and not S["sb"] and sf and c[i] < sup_lv - atr[i] * 0.10
        if up:
            S["rb"] = True
        if dn:
            S["sb"] = True
        lok = (not use_mom) or ao[i] > ao[i - 1]
        sok = (not use_mom) or ao[i] < ao[i - 1]
        can_l = up and lok and ((pos <= 0) if reverse else (pos == 0))
        can_s = dn and sok and ((pos >= 0) if reverse else (pos == 0))
        if can_l:
            sl = c[i] - atr[i] * 1.5 if stop_mode == "ATR" else swl[i] - atr[i] * 0.25
            S["risk"] = max(c[i] - sl, atr[i] * 0.5)
            out.append(("entry", "Long", 1, QTY))
        if can_s:
            sl = c[i] + atr[i] * 1.5 if stop_mode == "ATR" else swh[i] + atr[i] * 0.25
            S["risk"] = max(sl - c[i], atr[i] * 0.5)
            out.append(("entry", "Short", -1, QTY))
        in_l, in_s = pos > 0, pos < 0
        new = (in_l and not S["pl"]) or (in_s and not S["ps"])
        S["pl"], S["ps"] = in_l, in_s
        r = S["risk"]
        if not (in_l or in_s):
            S.update(stop=np.nan, tp=np.nan, be=False, tr=False)
        elif new:
            S.update(stop=avg - r if in_l else avg + r, tp=avg + r * 2.0 if in_l else avg - r * 2.0, be=False, tr=False)
        elif in_l:
            if not S["be"] and h[i] >= avg + r * 1.0:
                S["stop"], S["be"] = max(S["stop"], avg), True
            if S["tr"] or h[i] >= avg + r * 1.5:
                S["tr"] = True
                S["stop"] = max(S["stop"], c[i] - atr[i] * 2.0)
        else:
            if not S["be"] and l[i] <= avg - r * 1.0:
                S["stop"], S["be"] = min(S["stop"], avg), True
            if S["tr"] or l[i] <= avg - r * 1.5:
                S["tr"] = True
                S["stop"] = min(S["stop"], c[i] + atr[i] * 2.0)
        if (in_l or in_s) and not np.isnan(S["stop"]):
            nm = "L" if in_l else "S"
            side = "Long" if in_l else "Short"
            out.append(("exit", f"X{nm}", side, tp_pct if use_tp else None, S["stop"], S["tp"] if use_tp else None))
            if use_tp and tp_pct < 100:
                out.append(("exit", f"X{nm}-Rest", side, None, S["stop"], None))
        return out

    return simulate_brackets(o, h, l, c, orders, pyramiding=1, qty_step=1e-9)


def check():
    df = bars(8000, seed=15, freq="D")
    lc = np.log(df["close"].to_numpy() / 100)
    det = lc - np.polyval(np.polyfit(np.arange(len(lc)), lc, 1), np.arange(len(lc)))
    rel = {k: df[k].to_numpy() / df["close"].to_numpy() for k in ("open", "high", "low", "close")}
    for k in rel:
        df[k] = 100 * np.exp(0.5 * det) * rel[k] ** 0.5
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ov = {"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}
    cases = (({}, {}),
             ({"Stop Mode": "Swing", "Take Profit Quantity %": 50}, dict(stop_mode="Swing", tp_pct=50.0)),
             ({"Reverse on Opposite Signal": False, "Momentum Filter (smoothed AO turning)": False, "Use Take Profit": False},
              dict(reverse=False, use_mom=False, use_tp=False)))
    msgs, ok_all = [], True
    for params, kw in cases:
        ref = reference(df, **kw)
        ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params, strategy_overrides=ov), ref)
        ok_all = ok_all and ok and len(ref) > 12
        msgs.append(f"{d} (got {len(ref)})")
    return ok_all, " | ".join(msgs)
