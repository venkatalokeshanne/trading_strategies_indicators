"""Independent check — VWAP % Distance Scalper (Q6VGUgz1): 5-minute bars (24 h synthetic, price ~100) of a stock-style symbol, one contract per entry, pyramiding 2, market orders at the next open, commission / slippage off.
Percent distance of the close from the session VWAP (09:30 New York anchor), its 20-bar population standard deviation, the 1 / 2 / 3-sigma bands, the previous-daily 20 EMA ([1] inside the daily security, lookahead off), the expansion filter (sd above the max of the previous 3 sd), the re-entry of the 3-sigma band, the second contract under the average price, the 5-bar stop set on the entry bar and moved to the entry price after +6 points, and the band / VWAP limit target (re-issued every bar) are restated bar by bar.
Uses the quantity-aware bracket reference (indep.simulate_brackets). Variants: defaults (RTH, band 1 target); ETH session with the VWAP target and no expansion filter; band 2 target with a 2-bar stop lookback, expansion 2 and shorts only."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_ema, np_periods, np_security_lookahead_off, np_vwap, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "Q6VGUgz1"
BASE = dict(sess="RTH", target="Band 1", expand=3, use_exp=True, lookback=5, longs=True, shorts=True)


def rolling(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


def one(df, params, p):
    p = {**BASE, **p}
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    loc = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (loc.dt.hour * 60 + loc.dt.minute).to_numpy()
    sess = ((mins >= 570) & (mins < 960)) if p["sess"] == "RTH" else ((mins >= 1080) | (mins < 1020))
    vw = np_vwap(df, (h + l + c) / 3)
    pct = (c - vw) / vw * 100
    sd = rolling(pct, 20, np.std)
    pid, last_of = np_periods(df, 1440)
    dc = pd.Series(c).groupby(pid).last().to_numpy()
    de = np_ema(dc, 20)
    lagged = np.r_[np.nan, de[:-1]]                               # ema(close, 20)[1] on the daily series
    trend = np_security_lookahead_off(lagged, pid, last_of)
    sd_prev = np.r_[np.nan, sd[:-1]]
    sd_hi = rolling(sd_prev, p["expand"], np.max)
    lowest, highest = rolling(l, p["lookback"], np.min), rolling(h, p["lookback"], np.max)
    S = dict(stop=np.nan, prev=None)

    def orders(i, info):
        out = []
        pos, avg = info["pos"], info["avg"]
        u1, u2, u3 = sd[i] * 1.0, sd[i] * 2.0, sd[i] * 3.0
        band = {"Band 1": u1, "Band 2": u2, "Band 3": u3}.get(p["target"])
        lt = vw[i] * (1 - band / 100) if band is not None else vw[i]
        st_ = vw[i] * (1 + band / 100) if band is not None else vw[i]
        with np.errstate(invalid="ignore"):
            up, dn = c[i] > trend[i], c[i] < trend[i]
            expanding = (sd[i] > sd_hi[i]) if p["use_exp"] else True
            ltg = i > 0 and pct[i - 1] < -sd[i - 1] * 3.0 and pct[i] >= -u3
            stg = i > 0 and pct[i - 1] > sd[i - 1] * 3.0 and pct[i] <= u3
        flat = pos == 0
        if flat and ltg and sess[i] and expanding and up and p["longs"]:
            out.append(("entry", "Long", 1, 1.0))
        if flat and stg and sess[i] and expanding and dn and p["shorts"]:
            out.append(("entry", "Short", -1, 1.0))
        if pos > 0 and ltg and sess[i] and expanding and up and p["longs"] and c[i] < avg:
            out.append(("entry", "Long2", 1, 1.0))
        if pos > 0:
            if np.isnan(S["stop"]) or i == info["lots"][0]["eb"]:
                S["stop"] = lowest[i]
            elif h[i] - avg >= 6.0:
                S["stop"] = max(S["stop"], avg)
            out.append(("exit", "Long Exit", "", None, S["stop"], lt))
        if pos < 0:
            if np.isnan(S["stop"]) or i == info["lots"][0]["eb"]:
                S["stop"] = highest[i]
            elif avg - l[i] >= 6.0:
                S["stop"] = min(S["stop"], avg)
            out.append(("exit", "Short Exit", "", None, S["stop"], st_))
        if flat:
            S["stop"] = np.nan
        return [(a[0], *[None if (isinstance(x, float) and np.isnan(x)) else x for x in a[1:]]) for a in out]

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=2, tick=0.01, qty_step=1e-9)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


def check():
    df = bars(60000, seed=91, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.25
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Trading Session": "ETH", "Profit Target": "VWAP", "Use Expansion Filter": False}, dict(sess="ETH", target="VWAP", use_exp=False)),
             ({"Profit Target": "Band 2", "Stop Lookback (bars)": 2, "Bands Wider Than Max Of Prior X Bars": 2, "Enable Long Entries": False}, dict(target="Band 2", lookback=2, expand=2, longs=False)))
    for params, ov in cases:
        ok, m = one(df, params, ov)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
