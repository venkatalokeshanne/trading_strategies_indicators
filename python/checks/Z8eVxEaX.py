"""Independent check — Silver Surfer (Z8eVxEaX): 15-minute bars (24 h synthetic) of a crypto-style symbol (60-minute periods from 00:00 UTC), market orders at the next open, default quantity 1, commission / slippage / margin off.
The CISD state machine (inside bar = lower high and higher low than the previous bar; after a down candle that is not inside the trigger bull_t = its open, after an up candle bear_t = its open; Bullish when the close crosses over bull_t - the crossover compares with the trigger's previous value - Bearish when it crosses under bear_t) runs on the 15-minute chart and on the 60-minute period bars (period OHLC; lookahead off:
a period's state shows on its last chart bar, the previous period's before that). Entry while flat when both states agree, a fair-value gap versus two bars back is present and (optionally) the bar broke the previous bar's 10-bar extreme; while in a position one exit order is re-issued every bar around the close (stop 1.5 ATR, target RR x that).
Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too. Variants: defaults; BOS filter on; RR 2.5 with the BOS filter on."""
import numpy as np

from indep import bars, compare_q, np_atr, np_periods, np_security_lookahead_off, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "Z8eVxEaX"


def cisd(o, h, l, c):
    n = len(c)
    st = np.zeros(n)
    bull = bear = pbull = pbear = np.nan
    state = 0
    for i in range(n):
        inside = i > 0 and h[i] < h[i - 1] and l[i] > l[i - 1]
        if not np.isnan(bull) and i > 0 and c[i] > bull and c[i - 1] <= pbull:
            state = 1
        if not np.isnan(bear) and i > 0 and c[i] < bear and c[i - 1] >= pbear:
            state = -1
        if c[i] < o[i] and not inside:
            bull = o[i]
        if c[i] > o[i] and not inside:
            bear = o[i]
        pbull, pbear = bull, bear
        st[i] = state
    return st


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    pid, last_of = np_periods(df, 60, start_minutes=0, tz="UTC")
    nper = int(pid.max()) + 1
    po, ph, pl, pc = (np.zeros(nper) for _ in range(4))
    seen = np.zeros(nper, bool)
    for i in range(n):
        k = pid[i]
        if not seen[k]:
            po[k], ph[k], pl[k], seen[k] = o[i], h[i], l[i], True
        ph[k], pl[k], pc[k] = max(ph[k], h[i]), min(pl[k], l[i]), c[i]
    sh = np_security_lookahead_off(cisd(po, ph, pl, pc), pid, last_of)
    sl_ = cisd(o, h, l, c)
    atr = np_atr(h, l, c, 14)
    hh = np.array([h[i - 9:i + 1].max() if i >= 9 else np.nan for i in range(n)])
    ll = np.array([l[i - 9:i + 1].min() if i >= 9 else np.nan for i in range(n)])

    def orders(i, info):
        out = []
        pos = info["pos"]
        with np.errstate(invalid="ignore"):
            ab = sh[i] == 1 and sl_[i] == 1
            abr = sh[i] == -1 and sl_[i] == -1
            bb = i > 0 and h[i] > hh[i - 1]
            bs = i > 0 and l[i] < ll[i - 1]
            fb = i >= 2 and l[i] > h[i - 2]
            fs = i >= 2 and h[i] < l[i - 2]
        if ab and ((not p["bos"]) or bb) and fb and pos == 0:
            out.append(("entry", "Long", 1, 1.0))
        if abr and ((not p["bos"]) or bs) and fs and pos == 0:
            out.append(("entry", "Short", -1, 1.0))
        if pos != 0:
            d = atr[i] * 1.5
            if pos > 0:
                out.append(("exit", "LE", "Long", None, c[i] - d, c[i] + d * p["rr"]))
            else:
                out.append(("exit", "SE", "Short", None, c[i] + d, c[i] - d * p["rr"]))
        return out

    ref = simulate_brackets(o, h, l, c, orders)
    sym = SymbolInfo.make("BINANCE:XYZUSDT", "crypto", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(rr=1.5, bos=False)


def check():
    df = bars(30000, seed=371, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    cases = (({}, {}), ({"Require BOS Filter?": True}, dict(bos=True)), ({"Require BOS Filter?": True, "Risk-Reward Ratio": 2.5}, dict(bos=True, rr=2.5)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
