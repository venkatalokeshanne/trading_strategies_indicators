"""Independent check — Canuck Trading KAMA (YP4axuGh). Orders fill at the bar close (process_orders_on_close). KAMA, its bands,
slope and efficiency ratio are rebuilt in numpy (including the restart-from-close whenever kama[1] is na); the per-bar position
logic (Hold / Exit / Adaptive trims and reloads with strategy.close(qty=) and strategy.order) is replayed against the
quantity-aware reference broker, which shows the script the position as it stood before this bar's orders fill."""
import numpy as np

from indep import bars, compare_q, np_ema, np_sma, run_conversion, simulate_brackets

TV_ID = "YP4axuGh"
QTY = 100.0


def series(o, h, l, c, ER=10, FAST=2, SLOW=30, DEV=20):
    n = len(c)
    fast_sc, slow_sc = 2 / (FAST + 1), 2 / (SLOW + 1)
    er = np.full(n, np.nan)
    for i in range(ER, n):
        path = np.abs(np.diff(c[i - ER:i + 1])).sum()
        er[i] = (abs(c[i] - c[i - ER]) / path if path != 0 else 0.0)
    er0 = np.where(np.isnan(er), np.nan, er)
    sc = (er0 * (fast_sc - slow_sc) + slow_sc) ** 2
    kama = np.full(n, np.nan)
    for i in range(n):
        kama[i] = c[i] if (i == 0 or np.isnan(kama[i - 1])) else kama[i - 1] + sc[i] * (c[i] - kama[i - 1])
    dev = np.sqrt(np_sma((c - kama) ** 2, DEV))
    up, lo = kama + 2.0 * dev, kama - 2.0 * dev
    width = up - lo
    with np.errstate(divide="ignore", invalid="ignore"):
        bpos = np.where(width > 0, (c - lo) / width, 0.5)
        dist = np.where(dev > 0, (c - kama) / dev, 0.0)
    slope = np_ema(kama - np.r_[np.nan, kama[:-1]], 3)
    accel = slope > np.r_[np.nan, slope[:-1]]
    choppy = sc < np.sqrt(slow_sc ** 2 * fast_sc ** 2)
    acc1 = np.r_[False, accel[:-1]]
    green = ~choppy & (slope > 0) & (accel | acc1) & (c > kama)
    red = ~choppy & (slope < 0) & ~accel & ~acc1 & (c < kama)
    er_avg = np_ema(er, DEV)
    erc = np_ema(np.abs(er - np.r_[np.nan, er[:-1]]), 5)
    strong_thr = np.fmin(er_avg + erc * 4.0, 0.85)
    strong = (er >= strong_thr) & accel
    rng = h - l
    with np.errstate(divide="ignore", invalid="ignore"):
        wu = np.where(rng > 0, (h - np.maximum(o, c)) / rng, 0.0)
        wl = np.where(rng > 0, (np.minimum(o, c) - l) / rng, 0.0)
    rej_top = (wu > 0.4) & (bpos >= 0.67)
    rej_bot = (wl > 0.4) & (bpos <= 0.33)
    return dict(green=green, red=red, dist=np.abs(dist), dev=dev, strong=strong, rej_top=rej_top, rej_bot=rej_bot)


def reference(o, h, l, c, mode, direction):
    S = series(o, h, l, c)
    green, red = S["green"], S["red"]
    gray = ~green & ~red
    st = dict(oq=np.nan, peak=0.0, pct=1.0, bsa=0, prev_long=False, prev_short=False)

    def orders(i, info):
        pos = info["pos"]
        in_long, in_short = pos > 0, pos < 0
        in_trade, flat = in_long or in_short, pos == 0
        newpos = (in_long and not st["prev_long"]) or (in_short and not st["prev_short"])
        st["prev_long"], st["prev_short"] = in_long, in_short
        ad = S["dist"][i]
        if newpos:
            st.update(oq=abs(pos), peak=ad, pct=1.0, bsa=0)
        if flat:
            st.update(oq=np.nan, peak=0.0, pct=1.0, bsa=0)
        if in_trade and not newpos:
            st["bsa"] += 1
            st["peak"] = max(st["peak"], ad)
        dev_ok = ad <= 1.5
        out = []
        if mode == "Hold":
            if in_long and red[i]:
                out.append(("close", "Long"))
            if in_short and green[i]:
                out.append(("close", "Short"))
        elif mode == "Exit":
            if in_long and not green[i]:
                out.append(("close", "Long"))
            if in_short and not red[i]:
                out.append(("close", "Short"))
        elif in_trade and not newpos:
            if in_long and red[i]:
                out.append(("close", "Long"))
            elif in_short and green[i]:
                out.append(("close", "Short"))
            elif st["oq"] > 0:
                shift = 0.5 if S["strong"][i] else 0.0
                pa = -0.25 if ((in_long and S["rej_top"][i]) or (in_short and S["rej_bot"][i])) else 0.0
                thr = 1.0 + max(shift + pa, 0.0) - (0.25 if gray[i] else 0.0)
                step, minf = 0.20, 0.25
                depth = (ad - thr) / max(thr * 0.5, 0.25) if ad > thr else 0.0
                tp = max(1.0 - min(depth * step, 1.0 - minf), minf)
                cok = (in_long and green[i]) or (in_short and red[i])
                if ad < st["peak"] * 0.5 and cok:
                    tp = max(tp, min(st["pct"] + step, 1.0))
                if st["bsa"] >= 2 and abs(tp - st["pct"]) >= step * 0.5:
                    delta = max(st["oq"] * tp, 1.0) - abs(pos)
                    ident = "Long" if in_long else "Short"
                    if delta < 0 and abs(delta) >= 1.0:
                        out.append(("close_qty", ident, abs(delta)))
                        st.update(pct=tp, bsa=0)
                    elif delta > 0 and cok and dev_ok:
                        out.append(("order", ident, 1 if in_long else -1, delta))
                        st.update(pct=tp, bsa=0)
        if flat and green[i] and dev_ok and direction != "Short":
            out.append(("entry", "Long", 1, QTY))
        if flat and red[i] and dev_ok and direction != "Long":
            out.append(("entry", "Short", -1, QTY))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, on_close=True, qty_step=1e-9)
    return [r for r in ref if r[5] > 1e-9]      # float dust left on a trimmed lot is not a trade


def check():
    df = bars(20000, seed=17, freq="D")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    from pinelib import SymbolInfo
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ov = {"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}
    msgs, ok_all = [], True
    for mode, direction in (("Hold", "Long"), ("Hold", "Both"), ("Exit", "Both"), ("Adaptive", "Both"), ("Adaptive", "Long")):
        ref = reference(o, h, l, c, mode, direction)
        params = {"Trade Behaviour": mode, "Trade Direction": direction}
        ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params, strategy_overrides=ov), ref, tol=1e-7)   # quantities may differ in the 9th decimal (qty_step rounding of a trim)
        ok_all = ok_all and ok and len(ref) > 12
        msgs.append(f"{mode}/{direction}: {d} (got {len(ref)})")
    return ok_all, " | ".join(msgs)
