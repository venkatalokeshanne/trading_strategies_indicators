"""Independent check — SMC Pro v3 (lZ8kDfrb), 15-minute bars (24 h synthetic, UTC days), market entries at the next open, fixed 10
units, commission 0. Swing pivots (5 bars each side), the previous-day high / low from daily periods (lookahead on: every bar of a day
shows the previous day's value), the barssince sweep window, the latest bullish / bearish fair-value gap and displacement zone, the
discount / premium half of the 40-bar range and the EMA trend are rebuilt in numpy; the stop (signal bar extreme), 2 R limit and
break-even move are replayed against the quantity-aware reference broker."""
import numpy as np

from indep import bars, compare_q, np_atr, np_ema, np_periods, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "lZ8kDfrb"
QTY = 10.0
TICK = 0.01


def roll(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


def reference(df, swing_stop=True, trend_f=True, pd_f=True, confirm=True, trailing=False, be=True):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr = np_atr(h, l, c, 14)
    ef, es = np_ema(c, 20), np_ema(c, 50)
    pid, last_of = np_periods(df, 1440, start_minutes=0, tz="UTC")
    day_h = np.array([h[pid == p].max() for p in range(pid.max() + 1)])
    day_l = np.array([l[pid == p].min() for p in range(pid.max() + 1)])
    pdh = np.array([day_h[p - 1] if p > 0 else np.nan for p in pid])
    pdl = np.array([day_l[p - 1] if p > 0 else np.nan for p in pid])
    eq = (roll(h, 40, np.max) + roll(l, 40, np.min)) / 2
    S = dict(sh=np.nan, sl=np.nan, bf=None, sf=None, bz=None, sz=None, last_sweep_bull=None, last_sweep_bear=None,
             L=dict(e=np.nan, sl=np.nan, tp=np.nan, r=np.nan), Sh=dict(e=np.nan, sl=np.nan, tp=np.nan, r=np.nan))

    def orders(i, info):
        out = []
        P = 5
        if i >= 2 * P:
            j = i - P
            w = h[j - P:j + P + 1]
            if h[j] == w.max() and (w == h[j]).sum() == 1:
                S["sh"] = h[j]
            w = l[j - P:j + P + 1]
            if l[j] == w.min() and (w == l[j]).sum() == 1:
                S["sl"] = l[j]
        bear_sweep = not np.isnan(S["sh"]) and h[i] > S["sh"] and c[i] < S["sh"]
        bull_sweep = not np.isnan(S["sl"]) and l[i] < S["sl"] and c[i] > S["sl"]
        pdh_sw = h[i] > pdh[i] and c[i] < pdh[i]
        pdl_sw = l[i] < pdl[i] and c[i] > pdl[i]
        if bear_sweep or pdh_sw:
            S["last_sweep_bear"] = i
        if bull_sweep or pdl_sw:
            S["last_sweep_bull"] = i
        rb = S["last_sweep_bull"] is not None and i - S["last_sweep_bull"] <= 8
        rs = S["last_sweep_bear"] is not None and i - S["last_sweep_bear"] <= 8
        if i >= 2:
            if l[i] > h[i - 2] and (l[i] - h[i - 2]) > atr[i] * 0.15:
                S["bf"] = (l[i], h[i - 2])
            if h[i] < l[i - 2] and (l[i - 2] - h[i]) > atr[i] * 0.15:
                S["sf"] = (l[i - 2], h[i])
        if i >= 1:
            if c[i] > h[i - 1] and (c[i] - o[i]) > atr[i] * 0.8 and c[i - 1] < o[i - 1]:
                S["bz"] = (max(o[i - 1], c[i - 1]), l[i - 1])
            if c[i] < l[i - 1] and (o[i] - c[i]) > atr[i] * 0.8 and c[i - 1] > o[i - 1]:
                S["sz"] = (h[i - 1], min(o[i - 1], c[i - 1]))
        in_bf = S["bf"] is not None and l[i] <= S["bf"][0] and h[i] >= S["bf"][1]
        in_sf = S["sf"] is not None and h[i] >= S["sf"][1] and l[i] <= S["sf"][0]
        in_bz = S["bz"] is not None and l[i] <= S["bz"][0] and h[i] >= S["bz"][1]
        in_sz = S["sz"] is not None and h[i] >= S["sz"][1] and l[i] <= S["sz"][0]
        h1, l1 = (h[i - 1], l[i - 1]) if i else (np.nan, np.nan)
        bconf = (c[i] > o[i] and c[i] > h1) if confirm else c[i] > o[i]
        sconf = (c[i] < o[i] and c[i] < l1) if confirm else c[i] < o[i]
        long_ok = rb and (in_bz or in_bf) and bconf and ((not pd_f) or c[i] < eq[i]) and ((not trend_f) or ef[i] > es[i])
        short_ok = rs and (in_sz or in_sf) and sconf and ((not pd_f) or c[i] > eq[i]) and ((not trend_f) or ef[i] < es[i])
        flat = info["pos"] == 0
        if long_ok and flat:
            L = S["L"]
            L["e"] = c[i]
            L["sl"] = l[i] if swing_stop else c[i] - atr[i] * 1.0
            L["r"] = L["e"] - L["sl"]
            L["tp"] = L["e"] + L["r"] * 2.0
            if L["r"] > TICK:
                out.append(("entry", "Long", 1, QTY))
        if short_ok and flat:
            Sh = S["Sh"]
            Sh["e"] = c[i]
            Sh["sl"] = h[i] if swing_stop else c[i] + atr[i] * 1.0
            Sh["r"] = Sh["sl"] - Sh["e"]
            Sh["tp"] = Sh["e"] - Sh["r"] * 2.0
            if Sh["r"] > TICK:
                out.append(("entry", "Short", -1, QTY))
        pos = info["pos"]
        L, Sh = S["L"], S["Sh"]
        if pos > 0:
            cs = L["sl"]
            if be and not np.isnan(L["e"]) and not np.isnan(L["r"]) and h[i] >= L["e"] + L["r"]:
                cs = max(cs, L["e"])
            if trailing:
                cs = max(cs, c[i] - atr[i] * 1.0)
            if not np.isnan(cs) and not np.isnan(L["tp"]):
                out.append(("exit", "Long Exit", "Long", None, cs, L["tp"]))
        if pos < 0:
            cs = Sh["sl"]
            if be and not np.isnan(Sh["e"]) and not np.isnan(Sh["r"]) and l[i] <= Sh["e"] - Sh["r"]:
                cs = min(cs, Sh["e"])
            if trailing:
                cs = min(cs, c[i] + atr[i] * 1.0)
            if not np.isnan(cs) and not np.isnan(Sh["tp"]):
                out.append(("exit", "Short Exit", "Short", None, cs, Sh["tp"]))
        return out

    return simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=TICK, qty_step=1e-9)


def check():
    df = bars(30000, seed=7, freq="15min")
    lc = np.log(df["close"].to_numpy() / 100)
    det = lc - np.polyval(np.polyfit(np.arange(len(lc)), lc, 1), np.arange(len(lc)))
    rel = {k: df[k].to_numpy() / df["close"].to_numpy() for k in ("open", "high", "low", "close")}
    for k in rel:
        df[k] = 100 * np.exp(0.5 * det) * rel[k] ** 0.5
    sym = SymbolInfo.make("BINANCE:BTCUSDT", "crypto", qty_step=1e-9)
    ov = {"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}
    cases = (({}, {}),
             ({"Use Premium / Discount Filter": False, "Use EMA Trend Filter": False, "Require Confirmation Break": False},
              dict(pd_f=False, trend_f=False, confirm=False)),
             ({"Use Signal Candle Swing Stop": False, "Use Trailing Stop": True, "Move Stop to Breakeven at 1R": False},
              dict(swing_stop=False, trailing=True, be=False)))
    msgs, ok_all = [], True
    for params, kw in cases:
        ref = reference(df, **kw)
        ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides=ov), ref)
        ok_all = ok_all and ok and len(ref) > 12
        msgs.append(f"{d} (got {len(ref)})")
    return ok_all, " | ".join(msgs)
