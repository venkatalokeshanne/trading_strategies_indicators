"""Independent check — Fracture Threshold Strategy (NwMwuyA5): hourly bars of a 24 h market (UTC), market orders at the next open. Seven-point trend score (EMA4 > EMA5, RSI14 > 50, close > EMA21, EMA21 > SMA50, SMA50 > EMA55, EMA55 > EMA89, close > EMA750; mirrored for shorts) must reach the minimum, the EMA3-smoothed ratio SMA10(vol)/max(SMA40(vol),1) must be at least the floor, and the hour of the chosen time zone must lie in the London (08-17) or New York (14-21) window; the EMA4/5 cross (or the first bar with EMA4 beyond EMA5) enters while flat. The stop (ATR14 x 1.5) and target (x reward/risk) are measured from the SIGNAL close and issued with the entry, so they work from the fill bar. Uses the pending-order reference broker (simulate_ord). Commission / slippage / margin off on the pinelib side.
Variants: defaults; state trigger with score 4 and London only in Europe/London time; no session filter, min score 6, reward/risk 2; Asia/Tokyo window, vol floor 0.6."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_rsi, np_sma, run_conversion, simulate_ord

TV_ID = "NwMwuyA5"


def ema_na(x, n):
    out = np.full(len(x), np.nan)
    idx = np.flatnonzero(~np.isnan(x))
    if len(idx) < n:
        return out
    s = idx[0] + n - 1
    out[s] = x[idx[0]:s + 1].mean()
    k = 2.0 / (n + 1)
    for i in range(s + 1, len(x)):
        out[i] = k * x[i] + (1 - k) * out[i - 1]
    return out


def one(df, params, tz, sess, lon, ny, cross, minsc, vmin, rr, mult=1.5):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    loc = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert(tz)
    m = (loc.dt.hour * 60 + loc.dt.minute).to_numpy()
    e4, e5, e21, e55, e89, e750 = (np_ema(c, k) for k in (4, 5, 21, 55, 89, 750))
    s50 = np_sma(c, 50)
    rsi = np_rsi(c, 14)
    atr = np_atr(h, l, c, 14)
    vr = ema_na(np_sma(v, 10) / np.fmax(np_sma(v, 40), 1.0), 3)
    with np.errstate(invalid="ignore"):
        c1b, c1s = e4 > e5, e4 < e5
        bs = c1b.astype(int) + (rsi > 50) + (c > e21) + (e21 > s50) + (s50 > e55) + (e55 > e89) + (c > e750)
        ss = c1s.astype(int) + (rsi < 50) + (c < e21) + (e21 < s50) + (s50 < e55) + (e55 < e89) + (c < e750)
        vok = vr >= vmin
        pe4, pe5 = np.r_[np.nan, e4[:-1]], np.r_[np.nan, e5[:-1]]
        xu = (e4 > e5) & (pe4 <= pe5)
        xd = (e4 < e5) & (pe4 >= pe5)
    inl = (m >= 480) & (m < 1020)
    inn = (m >= 840) & (m < 1260)
    sok = ~np.full(n, sess) | (np.full(n, lon) & inl) | (np.full(n, ny) & inn)
    pb = np.r_[False, c1b[:-1]]
    ps = np.r_[False, c1s[:-1]]
    bt = xu if cross else (c1b & ~pb)
    st_ = xd if cross else (c1s & ~ps)

    def orders(i, pos):
        out = []
        sd = atr[i] * mult
        if bt[i] and bs[i] >= minsc and vok[i] and sok[i] and pos == 0:
            out += [("entry", "Long", 1, None, None), ("exit", "Long Exit", "Long", c[i] - sd, c[i] + sd * rr)]
        if st_[i] and ss[i] >= minsc and vok[i] and sok[i] and pos == 0:
            out += [("entry", "Short", -1, None, None), ("exit", "Short Exit", "Short", c[i] + sd, c[i] - sd * rr)]
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate_ord(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, tf="60", params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


def check():
    df = bars(5000, seed=313, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({}, ("America/New_York", True, True, True, True, 5, 0.9, 3.0)),
             ({"Timezone": "Europe/London", "Allow NY (14:00-21:00)": False, "EMA4/5 Cross Entry": False, "Min MasterTrend Score": 4},
              ("Europe/London", True, True, False, False, 4, 0.9, 3.0)),
             ({"Session Filter": False, "Min MasterTrend Score": 6, "Reward:Risk Ratio": 2.0}, ("America/New_York", False, True, True, True, 6, 0.9, 2.0)),
             ({"Timezone": "Asia/Tokyo", "Min Vol Ratio": 0.6, "Min MasterTrend Score": 4}, ("Asia/Tokyo", True, True, True, True, 4, 0.6, 3.0)))
    for params, args in cases:
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
