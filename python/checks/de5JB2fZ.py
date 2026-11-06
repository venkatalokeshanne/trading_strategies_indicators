"""Independent check — Rangos Manipulados PRO (de5JB2fZ): 15-minute bars (24 h synthetic, price ~100) of a crypto-style symbol (60-minute periods from 00:00 UTC), market orders at the next open, default quantity 1, pyramiding 0, commission / slippage / margin off.
Session = bar open time 08:00 - 17:00 at Europe/Madrid. Hourly sweep flags from the hour bars (low under the previous hour's low and close back above it / high over the previous high and close back under it), mapped with lookahead off (an hour's flag shows on its last chart bar, the previous hour's before that).
Chart bar: low under the previous bar's low (buy) / high over the previous high (sell) plus the 'Simple' confirmation (up candle closing above the previous high) or the 'Institucional' one (body over 60 % of the range, range over 0.8 ATR, close in the top 20 %); entry while flat with an exit order (stop = bar extreme -/+ buffer pips x 10 ticks, limit at RR x risk).
Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too. Variants: defaults; Institucional mode with RR 1.5; Simple mode with a 10-pip buffer and RR 3."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_periods, np_security_lookahead_off, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "de5JB2fZ"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sym = SymbolInfo.make("BINANCE:XYZUSDT", "crypto", qty_step=1e-9)
    pip = sym.mintick * 10
    mad = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Europe/Madrid")
    mins = (mad.dt.hour * 60 + mad.dt.minute).to_numpy()
    sess = (mins >= 480) & (mins < 1020)
    pid, last_of = np_periods(df, 60, start_minutes=0, tz="UTC")
    nper = int(pid.max()) + 1
    ph, pl, pc = np.full(nper, -np.inf), np.full(nper, np.inf), np.zeros(nper)
    for i in range(n):
        k = pid[i]
        ph[k], pl[k], pc[k] = max(ph[k], h[i]), min(pl[k], l[i]), c[i]
    mp = lambda x: np_security_lookahead_off(x, pid, last_of)
    h1h, h1l, h1c = mp(ph), mp(pl), mp(pc)
    h1ph, h1pl = mp(np.r_[np.nan, ph[:-1]]), mp(np.r_[np.nan, pl[:-1]])
    atr = np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        mb = (h1l < h1pl) & (h1c > h1pl)
        ms = (h1h > h1ph) & (h1c < h1ph)

    def orders(i, info):
        out = []
        if i == 0:
            return out
        body, rng = abs(c[i] - o[i]), h[i] - l[i]
        with np.errstate(invalid="ignore"):
            if p["mode"] == "Simple":
                cb, cs = c[i] > o[i] and c[i] > h[i - 1], c[i] < o[i] and c[i] < l[i - 1]
            else:
                cb = c[i] > o[i] and body > rng * 0.6 and rng > atr[i] * 0.8 and c[i] >= h[i] - rng * 0.2
                cs = c[i] < o[i] and body > rng * 0.6 and rng > atr[i] * 0.8 and c[i] <= l[i] + rng * 0.2
            bs_ = sess[i] and mb[i] and l[i] < l[i - 1] and cb
            ss_ = sess[i] and ms[i] and h[i] > h[i - 1] and cs
        buf = p["buf"] * pip
        if bs_ and info["pos"] == 0:
            sl = l[i] - buf
            out += [("entry", "BUY", 1, 1.0), ("exit", "BUY TP/SL", "BUY", None, sl, c[i] + (c[i] - sl) * p["rr"])]
        if ss_ and info["pos"] == 0:
            sl = h[i] + buf
            out += [("entry", "SELL", -1, 1.0), ("exit", "SELL TP/SL", "SELL", None, sl, c[i] - (sl - c[i]) * p["rr"])]
        return out

    ref = simulate_brackets(o, h, l, c, orders)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(mode="Simple", rr=2.0, buf=4.0)


def check():
    df = bars(60000, seed=461, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Tipo de Confirmación": "Institucional", "Risk Reward": 1.5}, dict(mode="Institucional", rr=1.5)),
             ({"Buffer SL en pips": 10.0, "Risk Reward": 3.0}, dict(buf=10.0, rr=3.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
