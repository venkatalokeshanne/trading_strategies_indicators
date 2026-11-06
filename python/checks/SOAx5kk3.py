"""Independent check — Pure Structure & S/D (SOAx5kk3): 4-hour bars (2023-01-01 UTC window applies), one position, market entries at the next open. Swing high / low = latest confirmed pivot (10 bars each side, strict). A close crossing over the swing high (under the swing low) is a break of structure: structure -> bullish (bearish), remembering the swing low (high) as the invalidation level;
trend is the structure unless the close violates that level. On a BOS in trend the zone = the most recent down (up) candle among the previous 30 bars (the current bar if none). A touch (low <= zone top and high >= zone bottom) in trend with close > EMA200 (< for shorts) arms the setup; it disarms when trend breaks or the close falls under the demand bottom (above the supply top).
With the confirmation candle: armed, bullish bar closing above the previous high (bearish below the previous low). Entry when flat inside the window if reward / risk >= 1.5 with stop = zone bottom (top), limit = the latest swing high (low), placed with the entry (work from the fill bar). Variants: default, and without the macro filter / confirmation. Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "SOAx5kk3"
K = 10
T0 = 1672531200000


def one(df, params, use_filter, use_conf):
    o, h, l, c, t = (df[k].to_numpy() for k in ("open", "high", "low", "close", "time"))
    n = len(c)
    ema = np_ema(c, 200)
    ph, pl = np.full(n, np.nan), np.full(n, np.nan)
    for i in range(2 * K, n):
        j = i - K
        if h[j] > h[j - K:j].max() and h[j] > h[j + 1:i + 1].max():
            ph[i] = h[j]
        if l[j] < l[j - K:j].min() and l[j] < l[j + 1:i + 1].min():
            pl[i] = l[j]
    S = dict(sh=np.nan, sl=np.nan, vh=np.nan, vl=np.nan, bull=False, dem=None, sup=None, wl=False, ws=False)
    lev = {}
    log: list = []
    pcl = np.r_[np.nan, c[:-1]]

    def orders(i, pos):
        out = []
        if not np.isnan(ph[i]):
            S["sh"] = ph[i]
        if not np.isnan(pl[i]):
            S["sl"] = pl[i]
        bb = bool(np_cross_over(np.array([pcl[i], c[i]]), np.array([S["sh"], S["sh"]]))[1]) if i > 0 else False
        br = bool(np_cross_under(np.array([pcl[i], c[i]]), np.array([S["sl"], S["sl"]]))[1]) if i > 0 else False
        if bb:
            S["vl"], S["bull"] = S["sl"], True
        if br:
            S["vh"], S["bull"] = S["sh"], False
        tb = S["bull"] and (np.isnan(S["vl"]) or c[i] > S["vl"])
        tr = (not S["bull"]) and (np.isnan(S["vh"]) or c[i] < S["vh"])
        if bb and tb:
            idx = 0
            for k in range(1, 31):
                if i - k >= 0 and o[i - k] > c[i - k]:
                    idx = k
                    break
            S["dem"] = (h[i - idx], l[i - idx])
        if br and tr:
            idx = 0
            for k in range(1, 31):
                if i - k >= 0 and o[i - k] < c[i - k]:
                    idx = k
                    break
            S["sup"] = (h[i - idx], l[i - idx])
        td = S["dem"] is not None and l[i] <= S["dem"][0] and h[i] >= S["dem"][1]
        ts = S["sup"] is not None and h[i] >= S["sup"][1] and l[i] <= S["sup"][0]
        if tb and td and ((not use_filter) or c[i] > ema[i]):
            S["wl"] = True
        if (not tb) or (S["dem"] is not None and c[i] < S["dem"][1]):
            S["wl"] = False
        if tr and ts and ((not use_filter) or c[i] < ema[i]):
            S["ws"] = True
        if (not tr) or (S["sup"] is not None and c[i] > S["sup"][0]):
            S["ws"] = False
        ph1 = h[i - 1] if i else np.nan
        pl1 = l[i - 1] if i else np.nan
        trg_l = td if not use_conf else (S["wl"] and c[i] > o[i] and c[i] > ph1)
        trg_s = ts if not use_conf else (S["ws"] and c[i] < o[i] and c[i] < pl1)
        inw = t[i] >= T0
        net = sum((x[4] - x[2]) * x[0] * lev[x[1] - 1][2] for x in log)
        eq = 10000.0 + net            # flat at a signal, commission off: equity = capital + closed P&L
        if inw and trg_l and S["wl"] and pos == 0:
            sl, tp = S["dem"][1], S["sh"]
            rd = abs(c[i] - sl)
            rr = abs(tp - c[i]) / rd if rd > 0 else 0
            q = max(eq * 0.01 / rd, 0) if rd > 0 else 0
            if rr >= 1.5 and q > 0:
                out.append(("entry", 1))
                lev[i] = (sl, tp, q)
                S["wl"] = False
        if inw and trg_s and S["ws"] and pos == 0:
            sl, tp = S["sup"][0], S["sl"]
            rd = abs(sl - c[i])
            rr = abs(c[i] - tp) / rd if rd > 0 else 0
            q = max(eq * 0.01 / rd, 0) if rd > 0 else 0
            if rr >= 1.5 and q > 0:
                out.append(("entry", -1))
                lev[i] = (sl, tp, q)
                S["ws"] = False
        return out

    stop = lambda i, pos, ep, eb: lev[eb - 1][0] if eb - 1 in lev else None
    tgt = lambda i, pos, ep, eb: lev[eb - 1][1] if eb - 1 in lev else None
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt, log=log)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="240", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(60000, seed=801, freq="4h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100.0 * (df[k] / 100.0) ** 0.25          # tame the synthetic drift so equity stays positive (the 1 % risk sizing needs it)
    msgs, allok = [], True
    for params, uf, uc in (({}, True, True), ({"Use Macro Trend Filter": False, "Wait for Confirmation Candle": False}, False, False)):
        ok, m = one(df, params, uf, uc)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
