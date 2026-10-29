"""Independent check — NovaTrade IRB v2.0.0 (emAsZ8tc): 1-hour bars (24 h synthetic, price ~1.1 with 0.0001 buffers) on a US stock chart (4-hour periods counted from 09:30 New York), margin / commission / slippage off.
IRB bar: open and close in the lower (upper) 55% of the bar's range; with trend (EMA20 vs 20 bars ago over ATR >= 0.4), rising 4-hour EMA20 (lookahead off, vs 20 chart bars ago), ADX >= 20, range <= 2 ATR, EMA10 > EMA20 > EMA50 and N closes above EMA10 the script places a BUY STOP at high + buffer (sell stop mirrored) from the flat state; the order is re-issued on a same-direction signal and cancelled after 20 bars;
a fill moves the state machine to in-position (stop = max(irb low - buffer, trail EMA), ratcheted by the trail EMA each bar, exit issued while open at script time) and a close after 40 bars in the position; a closed position resets to flat (a same-bar new signal can then place an order). Uses the pending-order reference broker (simulate_ord).
Variants: defaults (3 confirm bars, trail EMA 40); 2 confirm bars, trail EMA 25; 4 confirm bars, trail EMA 60."""
import numpy as np

from indep import bars, compare, np_atr, np_dmi, np_ema, np_periods, np_security_lookahead_off, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "emAsZ8tc"
PB = 0.0001


def one(df, params, nconf, trail_len):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    e10, e20, e50 = np_ema(c, 10), np_ema(c, 20), np_ema(c, 50)
    tr = np_ema(c, trail_len)
    atr = np_atr(h, l, c, 14)
    adx = np_dmi(h, l, c, 14)[2]
    pid, last_of = np_periods(df, 240)
    h4 = np_security_lookahead_off(np_ema(c[last_of], 20), pid, last_of)
    S = dict(prev=None, state=0, ih=np.nan, il=np.nan, pb=0, pob=0, stop=np.nan)

    def orders(i, pos):
        out = []
        with np.errstate(invalid="ignore", divide="ignore"):
            rng = h[i] - l[i]
            warm = i >= max(50, nconf, trail_len)
            up_irb = rng > 0 and o[i] <= h[i] - 0.45 * rng and c[i] <= h[i] - 0.45 * rng
            dn_irb = rng > 0 and o[i] >= l[i] + 0.45 * rng and c[i] >= l[i] + 0.45 * rng
            back = e20[i - 20] if i >= 20 else np.nan
            slope = (e20[i] - (0.0 if np.isnan(back) else back)) / atr[i] if (not np.isnan(atr[i]) and atr[i] > 0) else 0.0
            t_up, t_dn = slope >= 0.4, slope <= -0.4
            hb = h4[i - 20] if i >= 20 else np.nan
            h4u = (not np.isnan(h4[i])) and (not np.isnan(hb)) and h4[i] > hb
            h4d = (not np.isnan(h4[i])) and (not np.isnan(hb)) and h4[i] < hb
            sw = adx[i] >= 20
            oe = rng / atr[i] if (not np.isnan(atr[i]) and atr[i] > 0) else 0.0
            oe_ok = oe <= 2.0
            sbull = e10[i] > e20[i] and e20[i] > e50[i]
            sbear = e10[i] < e20[i] and e20[i] < e50[i]
            cl = all((i - k >= 0) and not np.isnan(e10[i - k]) and c[i - k] > e10[i - k] for k in range(nconf))
            cs = all((i - k >= 0) and not np.isnan(e10[i - k]) and c[i - k] < e10[i - k] for k in range(nconf))
            sl = bool(warm and up_irb and t_up and h4u and sw and oe_ok and sbull and cl)
            ss = bool(warm and dn_irb and t_dn and h4d and sw and oe_ok and sbear and cs)
        prev = S["prev"]
        was_flat = prev == 0 if prev is not None else False
        fill_l, fill_s = pos > 0 and was_flat, pos < 0 and was_flat
        closed = pos == 0 and not was_flat
        if closed:
            S.update(state=0, ih=np.nan, il=np.nan, pb=0, pob=0, stop=np.nan)
        if fill_l and S["state"] == 1:
            S.update(state=3, pob=0, stop=S["il"] - PB)
        if fill_s and S["state"] == 2:
            S.update(state=4, pob=0, stop=S["ih"] + PB)
        if S["state"] in (1, 2):
            S["pb"] += 1
        if S["state"] in (3, 4):
            S["pob"] += 1
        if S["state"] == 1 and S["pb"] >= 20:
            out.append(("cancel", "Long"))
            S.update(state=0, ih=np.nan, il=np.nan, pb=0)
        if S["state"] == 2 and S["pb"] >= 20:
            out.append(("cancel", "Short"))
            S.update(state=0, ih=np.nan, il=np.nan, pb=0)
        if S["state"] == 0 and sl:
            out.append(("entry", "Long", 1, h[i] + PB, None))
            S.update(ih=h[i], il=l[i], state=1, pb=0)
        elif S["state"] == 0 and ss:
            out.append(("entry", "Short", -1, l[i] - PB, None))
            S.update(ih=h[i], il=l[i], state=2, pb=0)
        elif S["state"] == 1 and sl:
            out.append(("entry", "Long", 1, h[i] + PB, None))
            S.update(ih=h[i], il=l[i], pb=0)
        elif S["state"] == 2 and ss:
            out.append(("entry", "Short", -1, l[i] - PB, None))
            S.update(ih=h[i], il=l[i], pb=0)
        if S["state"] == 3:
            S["stop"] = max(S["stop"] if not np.isnan(S["stop"]) else tr[i], tr[i])
            out.append(("exit", "Long Exit", "Long", S["stop"], None))
            if S["pob"] >= 40:
                out.append(("close", "Long"))
        if S["state"] == 4:
            S["stop"] = min(S["stop"] if not np.isnan(S["stop"]) else tr[i], tr[i])
            out.append(("exit", "Short Exit", "Short", S["stop"], None))
            if S["pob"] >= 40:
                out.append(("close", "Short"))
        S["prev"] = pos
        return out

    ref = simulate_ord(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


def check():
    df = bars(30000, seed=71, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 1.1 * (df[k] / 100) ** 0.05
    msgs, allok = [], True
    cases = (({}, 3, 40),
             ({"Bars Closing Above/Below EMA 10": 2, "Trailing Stop EMA Period": 25}, 2, 25),
             ({"Bars Closing Above/Below EMA 10": 4, "Trailing Stop EMA Period": 60}, 4, 60))
    for params, nc, tl in cases:
        ok, m = one(df, params, nc, tl)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
