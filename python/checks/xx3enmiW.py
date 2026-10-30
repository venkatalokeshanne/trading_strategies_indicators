"""Independent check — Ichimoku Confluence Strategy (xx3enmiW): 1-hour continuous bars on a US stock chart (daily periods counted from 09:30 New York), market orders at the next open, commission / slippage / margin off (the quantity only needs to be positive: it is risk-based / capped / fixed % of equity and does not change trade prices).
Tenkan/Kijun crossover classed strong / neutral / weak against the cloud under the current bar (senkou spans displacement-1 bars ago); entry and exit tiers selectable; optional daily Tenkan > Kijun filter (period highs / lows, lookahead off); an entry while on the other side reverses.
Exits: ATR bracket re-issued from the close each bar (position open at script time), or fixed % from the average entry price, or none; plus the opposite-signal close. Uses the pending-order reference broker (simulate_ord).
Variants: defaults (long only, ATR); both sides with all tiers for entries / strong-only exits and fixed-% stops; short only, no HTF filter, no stops, shorter lengths."""
import numpy as np

from indep import bars, compare, np_atr, np_periods, np_security_lookahead_off, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "xx3enmiW"


def don(h, l, n):
    out = np.full(len(h), np.nan)
    for i in range(n - 1, len(h)):
        out[i] = (h[i - n + 1:i + 1].max() + l[i - n + 1:i + 1].min()) / 2.0
    return out


def tier(t, s, ne, w):
    return s if t == "Strong Only" else (s or ne if t == "Strong + Neutral" else (s or ne or w))


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    tk, kj = don(h, l, p["tk"]), don(h, l, p["kj"])
    sa = (tk + kj) / 2.0
    sb = don(h, l, p["sb"])
    d = p["disp"] - 1
    ca = np.r_[np.full(d, np.nan), sa[:n - d]] if d else sa
    cb = np.r_[np.full(d, np.nan), sb[:n - d]] if d else sb
    atr = np_atr(h, l, c, 14)
    pid, last_of = np_periods(df, 1440)
    npd = pid[-1] + 1
    ph = np.array([h[pid == k].max() for k in range(npd)])
    pl = np.array([l[pid == k].min() for k in range(npd)])
    htk = np_security_lookahead_off(don(ph, pl, p["tk"]), pid, last_of)
    hkj = np_security_lookahead_off(don(ph, pl, p["kj"]), pid, last_of)
    allow_l, allow_s = p["mode"] in ("Long", "Both"), p["mode"] in ("Short", "Both")

    def orders(i, pos, info):
        out = []
        with np.errstate(invalid="ignore"):
            top, bot = max(ca[i], cb[i]), min(ca[i], cb[i])
            bc = i > 0 and tk[i] > kj[i] and tk[i - 1] <= kj[i - 1]
            sc = i > 0 and tk[i] < kj[i] and tk[i - 1] >= kj[i - 1]
            lvl = tk[i]
            sbull, nbull, wbull = bc and lvl > top, bc and bot <= lvl <= top, bc and lvl < bot
            sbear, nbear, wbear = sc and lvl < bot, sc and bot <= lvl <= top, sc and lvl > top
            les, lxs = tier(p["el"], sbull, nbull, wbull), tier(p["xl"], sbear, nbear, wbear)
            ses, sxs = tier(p["es"], sbear, nbear, wbear), tier(p["xs"], sbull, nbull, wbull)
            hb = htk[i] > hkj[i]
            mok_l = (not p["mtf"]) or hb
            mok_s = (not p["mtf"]) or (not hb)
            sd = c[i] * p["sl"] / 100 if (p["stop"] == "Fixed %" and p["sl"] > 0) else atr[i] * 1.5
            qok = (sd > 0) if p["sizing"] == "risk" else True
        if allow_l and les and mok_l and pos <= 0 and qok:
            out.append(("entry", "Long", 1, None, None))
        if allow_s and ses and mok_s and pos >= 0 and qok:
            out.append(("entry", "Short", -1, None, None))
        for side, sign in (("Long", 1), ("Short", -1)):
            if pos * sign > 0:
                if p["stop"] == "ATR":
                    out.append(("exit", "L Exit" if sign > 0 else "S Exit", side, c[i] - sign * atr[i] * 1.5, c[i] + sign * atr[i] * 3.0))
                elif p["stop"] == "Fixed %":
                    sl = info["ep"] * (1 - sign * p["sl"] / 100) if p["sl"] > 0 else None
                    tp = info["ep"] * (1 + sign * p["tp"] / 100) if p["tp"] > 0 else None
                    out.append(("exit", "L Exit" if sign > 0 else "S Exit", side, sl, tp))
                if (lxs if sign > 0 else sxs):
                    out.append(("close", side))
        return out

    ref = simulate_ord(o, h, l, c, orders)
    ok, dd = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{dd} (got {len(ref)})"


BASE = dict(tk=9, kj=26, sb=52, disp=26, mode="Long", el="Strong + Neutral", xl="All (incl. Weak)", es="Strong + Neutral", xs="All (incl. Weak)",
            mtf=True, stop="ATR", sl=0.0, tp=0.0, sizing="risk")


def check():
    df = bars(20000, seed=5, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Direction": "Both", "Entry Tier (Bullish)": "All (incl. Weak)", "Entry Tier (Bearish)": "All (incl. Weak)", "Exit Tier (Bearish)": "Strong Only",
               "Exit Tier (Bullish)": "Strong Only", "Stop Mode": "Fixed %", "Take Profit % (Fixed mode)": 3.0, "Stop Loss % (Fixed mode)": 2.0},
              dict(mode="Both", el="All (incl. Weak)", es="All (incl. Weak)", xl="Strong Only", xs="Strong Only", stop="Fixed %", tp=3.0, sl=2.0)),
             ({"Direction": "Short", "Require HTF trend agreement": False, "Stop Mode": "None", "Tenkan-sen": 6, "Kijun-sen": 14, "Senkou Span B": 30, "Displacement": 14},
              dict(mode="Short", mtf=False, stop="None", tk=6, kj=14, sb=30, disp=14)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
