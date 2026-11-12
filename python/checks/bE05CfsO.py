"""Independent check — Quant Trend Engine Long Only (bE05CfsO): 4-hour bars (7 days a week), process_orders_on_close, long only, no pyramiding. Trend score (double-smoothed EMA18/50/120 stack, separation, slopes over 10 bars,
18-bar efficiency, 7-bar persistence / 12-bar momentum, ATR regime vs SMA40 of ATR, 20-bar prior-high breakout, pullback reclaim) enters at the close when flat, outside the weekend / Friday 16:00+ New York block, after the 5-bar
cooldown (last-exit bar is updated later in the script, so the bar that detects a close still sees the old value). `x != 0 ? a : b` with na x takes b. The position is seen at script time (a close fills at the same bar's close, so the
next bar is the first with the position flat); entryBarIndex = first script run with the position open, exits are enabled one bar later: from then on stop = max(avg * 0.98, ratcheting trail of close - 2.8 ATR vs
highest high since - 20.8 ATR) works from the next bar, and bearish crosses / structure break / weak score / failures close at the close (Friday 16:00 closes first). The leverage input only sizes the trade."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_ema, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "bE05CfsO"


def nz_ratio(a, b):
    """a / b where `b != 0` (na -> the false branch 0.0)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(~np.isnan(b) & (b != 0), a / b, 0.0)


def check_one(df, params):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sh = lambda x, k=1: np.r_[np.full(k, np.nan), x[:-k]] if k else x
    dsm = lambda x, L: np_ema(np_ema(x, L), 3)
    fast, mid, slow = dsm(c, 18), dsm(c, 50), dsm(c, 120)
    with np.errstate(invalid="ignore"):
        sep_ok = nz_ratio(np.abs(fast - slow), slow) * 100 >= 0.30
        sl = lambda x: nz_ratio(x - sh(x, 10), sh(x, 10)) * 100
        slope_ok = (sl(slow) >= 0.03) & (sl(mid) > 0) & (sl(fast) > 0)
        bull_stack = (fast > mid) & (mid > slow)
    net = np.abs(c - sh(c, 18))
    step = np.zeros(n)
    for k in range(1, 19):
        step = step + np.abs(sh(c, k - 1) - sh(c, k))
    eff = nz_ratio(net, step)
    with np.errstate(invalid="ignore"):
        eff_ok = eff >= 0.33
    up = np.zeros(n)
    for k in range(0, 7):
        with np.errstate(invalid="ignore"):
            up = up + (sh(c, k) > sh(c, k + 1))
    pr = up / 7
    mom = nz_ratio(c - sh(c, 12), sh(c, 12)) * 100
    mom_ok = (mom > 0) & (pr >= 0.57)
    atr = np_atr(h, l, c, 14)
    ab = np_sma(atr, 40)
    reg = nz_ratio(atr, ab)
    atr_ok = reg >= 0.95
    hh = sh(pd.Series(h).rolling(20, min_periods=20).max().to_numpy())
    bs = nz_ratio(c - hh, atr)
    with np.errstate(invalid="ignore"):
        breakout_ok = (c > hh) & (bs >= 0.15)
    pbl = pd.Series(l).rolling(8, min_periods=8).min().to_numpy()
    dfa = nz_ratio(fast - pbl, atr)
    with np.errstate(invalid="ignore"):
        deep = dfa >= 0.90
        rf = (c > fast) & (sh(c) <= sh(fast))
        rm = (c > mid) & (sh(c) <= sh(mid))
        rs = nz_ratio(c - fast, atr)
        reclaim_ok = (rf | rm) & (rs >= 0.15)
    bcross = np_cross_over(fast, mid) | np_cross_over(fast, slow) | np_cross_over(mid, slow)
    since = np.full(n, np.nan)
    last = -1
    for i in range(n):
        if bcross[i]:
            last = i
        since[i] = i - last if last >= 0 else np.nan
    with np.errstate(invalid="ignore"):
        birth = (since >= 0) & (since <= 14)
    score = (1.5 * bull_stack + 0.9 * sep_ok + 1.1 * slope_ok + 1.0 * eff_ok + 0.8 * atr_ok + 1.0 * mom_ok + 1.25 * breakout_ok + 1.1 * reclaim_ok)
    cont = bull_stack & breakout_ok & slope_ok & eff_ok & mom_ok
    pull = bull_stack & sep_ok & slope_ok & deep & reclaim_ok & eff_ok
    early = birth & bull_stack & sep_ok & slope_ok & atr_ok & mom_ok
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    dow, hr = ny.dt.dayofweek.to_numpy(), ny.dt.hour.to_numpy()          # Monday = 0 .. Sunday = 6
    weekend = dow >= 5
    fri = (dow == 4) & (hr >= 16)
    bcu = np_cross_under(fast, mid) | np_cross_under(fast, slow)
    with np.errstate(invalid="ignore"):
        sb = (c < mid) & (fast < mid)
        weak = score <= 2.5
        mf = (pr < 0.40) & (mom < 0)
        rf2 = (reg < 0.80) & (eff < 0.25)
        base_entry = (score >= 5.0) & (c > slow) & (cont | pull | early)
    S = dict(last_exit=None, ebi=None, hs=np.nan, trail=np.nan)
    poscl = np.zeros(n)
    stop_arr = np.full(n, np.nan)

    def orders(i, pos):
        poscl[i] = pos
        prev = poscl[i - 1] if i else np.nan
        out = []
        cool = S["last_exit"] is None or i - S["last_exit"] > 5
        if (not weekend[i]) and (not fri[i]) and pos == 0 and cool and base_entry[i]:
            out.append(("entry", 1))
        if pos > 0 and prev == 0:
            S["ebi"] = i
        can_exit = pos > 0 and S["ebi"] is not None and i > S["ebi"]
        if pos > 0:
            S["hs"] = h[i] if np.isnan(S["hs"]) else max(S["hs"], h[i])
            comb = max(c[i] - atr[i] * 2.8, S["hs"] - atr[i] * 20.8)
            S["trail"] = comb if np.isnan(S["trail"]) else max(S["trail"], comb)
        else:
            S["hs"] = S["trail"] = np.nan
        time_exit = pos > 0 and fri[i]
        exit_long = pos > 0 and can_exit and (bcu[i] or sb[i] or weak[i] or mf[i] or rf2[i])
        if pos > 0 and can_exit:
            hard = S["avg"] * 0.98
            stop_arr[i] = max(hard, S["trail"])
        if time_exit and can_exit:
            out.append(("close", 1))
        if prev > 0 and pos == 0:
            S["last_exit"], S["trail"], S["hs"], S["ebi"] = i, np.nan, np.nan, None
        if exit_long and not time_exit:
            out.append(("close", 1))
        return out

    def stop(i, pos, ep, eb):
        S["avg"] = ep
        if i == 0 or np.isnan(stop_arr[i - 1]) or poscl[i - 1] <= 0:
            return None
        return stop_arr[i - 1]

    def avg_capture(i, pos, ep, eb):
        return None

    # the average price at script time is the entry price (single lot): keep it current for orders()
    S["avg"] = np.nan
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, on_close=True)
    sym = SymbolInfo.make("BINANCE:BTCUSD", "crypto", qty_step=1e-9)
    res = run_conversion(TV_ID, df, symbol=sym, tf="240", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0})
    ok, d = compare(res, ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(12000, seed=551, freq="4h")
    ok, m = check_one(df, {})
    ok2, m2 = check_one(df, {"Min Entry Score": 4.0})
    return ok and ok2, m + " | " + m2
