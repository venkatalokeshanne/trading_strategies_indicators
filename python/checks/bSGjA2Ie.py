"""Independent check — Momentum Slope Navigator v1.1.1 (bSGjA2Ie), daily bars, orders at the bar close (process_orders_on_close),
commission / slippage 0. The squeeze-momentum histogram (linear regression of close minus the mean of the channel middle and
SMA), its N-bar rise / fall, the ATR and the position-state bookkeeping (extremes since entry, break-even, bars in trade) are
rebuilt in numpy; the per-bar exit orders (hard stop, break-even stop, partial limit, and the trailing exit activated at an
absolute price with a tick offset) are replayed against the quantity-aware reference broker. The script passes the trail offset
in price units where Pine reads ticks; the reference does the same (tick 0.01)."""
import numpy as np

from indep import bars, compare_q, np_atr, np_sma, np_tr, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "bSGjA2Ie"
TICK = 0.01


def roll(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


def linreg0(y, n):
    out = np.full(len(y), np.nan)
    x = np.arange(n, dtype=float)
    for i in range(n - 1, len(y)):
        w = y[i - n + 1:i + 1]
        if np.isnan(w).any():
            continue
        b, a = np.polyfit(x, w, 1)
        out[i] = a + b * (n - 1)
    return out


def reference(df, confirm=2, mode="Fixed Percent", trail=True, hard=True, be=False, partial=False, time_exit=None):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    rng = np_sma(np_tr(h, l, c, False), 20)
    mid = ((roll(h, 20, np.max) + roll(l, 20, np.min)) / 2 + np_sma(c, 20)) / 2
    val = linreg0(c - mid, 20)
    atr = np_atr(h, l, c, 14)

    def rising(i, k0, up):
        for k in range(confirm):
            a, b = val[i - k0 - k] if i - k0 - k >= 0 else np.nan, val[i - k0 - k - 1] if i - k0 - k - 1 >= 0 else np.nan
            if not ((a > b) if up else (a < b)):
                return False
        return True

    S = dict(hi=np.nan, lo=np.nan, eb=None, pl=False, ps=False)

    def pct(i, entry, fixed, mult):
        return fixed if mode == "Fixed Percent" else (atr[i] / entry * 100 * mult if entry != 0 else np.nan)

    def orders(i, info):
        out = []
        pos, ep = info["pos"], info["avg"]
        r_l = rising(i, 0, True) and not rising(i, 1, True)
        r_s = rising(i, 0, False) and not rising(i, 1, False)
        if r_l:
            out += [("close", "Short"), ("entry", "Long", 1, 1.0)]
        if r_s:
            out += [("close", "Long"), ("entry", "Short", -1, 1.0)]
        in_l, in_s = pos > 0, pos < 0
        new_l, new_s = in_l and not S["pl"], in_s and not S["ps"]
        S["pl"], S["ps"] = in_l, in_s
        if new_l or new_s:
            S.update(hi=h[i], lo=l[i], eb=i)
        elif in_l or in_s:
            S.update(hi=max(h[i], S["hi"]), lo=min(l[i], S["lo"]))
        else:
            S.update(hi=np.nan, lo=np.nan, eb=None)
        if not (in_l or in_s):
            return out
        hs = pct(i, ep, 2.0, 2.0)
        act = pct(i, ep, 3.0, 3.0)
        cb = pct(i, ep, 1.0, 1.0)
        bea = pct(i, ep, 1.5, 1.5)
        beo = pct(i, ep, 0.1, 0.1)
        ptp = pct(i, ep, 2.0, 2.0)
        for d, name, hi_lo in ((1, "Long", S["hi"]), (-1, "Short", S["lo"])):
            if (d == 1) != in_l:
                continue
            be_act = be and (hi_lo >= ep * (1 + bea / 100) if d == 1 else hi_lo <= ep * (1 - bea / 100))
            hard_px = ep * (1 - d * hs / 100) if hard else np.nan
            be_px = ep * (1 + d * beo / 100)
            if be_act:
                base = be_px if np.isnan(hard_px) else hard_px
                stop = max(base, be_px) if d == 1 else min(base, be_px)
            else:
                stop = hard_px
            stop = None if np.isnan(stop) else stop
            if partial:
                out.append(("exit", f"{name} Partial TP", name, 50.0, None, ep * (1 + d * ptp / 100)))
            if trail:
                out.append(("exit", f"{name} Protective Trail", name, None, stop, None, None, ep * (1 + d * act / 100), ep * (cb / 100)))
            else:
                out.append(("exit", f"{name} Protective Stop", name, None, stop, None))
            if time_exit and i - S["eb"] >= time_exit:
                out.append(("close", name))
        return out

    return simulate_brackets(o, h, l, c, orders, pyramiding=1, on_close=True, tick=TICK, qty_step=1e-9)


def check():
    df = bars(9000, seed=12, freq="D")
    lc = np.log(df["close"].to_numpy() / 100)
    det = lc - np.polyval(np.polyfit(np.arange(len(lc)), lc, 1), np.arange(len(lc)))
    rel = {k: df[k].to_numpy() / df["close"].to_numpy() for k in ("open", "high", "low", "close")}
    for k in rel:
        df[k] = 100 * np.exp(0.5 * det) * rel[k] ** 0.5
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ov = {"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}
    cases = (({}, {}),
             ({"Use Trailing Stop / Trailing Stop Kullan": False, "Use Break-Even / Başa Baş Kullan": True,
               "Use Partial TP / Kısmi Kar Al Kullan": True, "Use Time Exit / Süre Çıkışı Kullan": True, "Time Exit Bars / Süre Çıkışı Bar": 30},
              dict(trail=False, be=True, partial=True, time_exit=30)),
             ({"Exit Mode / Çıkış Modu": "ATR Based", "Consecutive Histogram Bars / Ardışık Histogram Barı": 3},
              dict(mode="ATR Based", confirm=3)))
    msgs, ok_all = [], True
    for params, kw in cases:
        ref = reference(df, **kw)
        ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params, strategy_overrides=ov), ref)
        ok_all = ok_all and ok and len(ref) > 12
        msgs.append(f"{d} (got {len(ref)})")
    return ok_all, " | ".join(msgs)
