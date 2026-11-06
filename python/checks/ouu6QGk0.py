"""Independent check — NQ range breakout, touch entry (ouu6QGk0): 5-minute bars (24 h synthetic, compressed), pending stop entries. In the chart timezone (Asia/Taipei) the high / low of the bars starting inside [start, end) form the day's range (reset when the day of the month changes); from the end time on, while the range is between 0.1 % and 1 % of its high and nothing has traded today, a buy-stop at high + 38.2 % of the range and a sell-stop at low - 38.2 % are (re)placed every bar together with exits ExL / ExS (stop = low + 10 % of the range / high - 10 %, target = high + 0.618 x range / low - 0.618 x range). As soon as a position is open or a trade has closed on a bar, "already traded" is set for the day and both pending entries are cancelled (the exits stay). Uses the pending-order reference broker (simulate_ord). Margin off on the pinelib side.
Variants: defaults with a 11:45-13:30 range; a 0.5 buffer ratio, 0.3 stop fraction and a 08:00-09:00 New York range."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion, simulate_ord

TV_ID = "ouu6QGk0"


def one(df, params, tz, sm, em, buf, tpr, slf):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    loc = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert(tz)
    m = (loc.dt.hour * 60 + loc.dt.minute).to_numpy()
    dom = loc.dt.day.to_numpy()
    log = []
    S = dict(rh=np.nan, rl=np.nan, done=False, prev_closed=0)

    def orders(i, pos):
        out = []
        pc = S["prev_closed"]
        S["prev_closed"] = len(log)
        if i > 0 and dom[i] != dom[i - 1]:
            S["rh"] = S["rl"] = np.nan
            S["done"] = False
        if sm <= m[i] < em:
            S["rh"] = h[i] if np.isnan(S["rh"]) else max(S["rh"], h[i])
            S["rl"] = l[i] if np.isnan(S["rl"]) else min(S["rl"], l[i])
        rh, rl = S["rh"], S["rl"]
        rp = (rh - rl) / rh
        over, under = rp > 0.01, rp < 0.001
        if pos != 0 or len(log) > pc:
            S["done"] = True
        if m[i] >= em and not np.isnan(rh) and not S["done"] and not over and not under:
            rs = rh - rl
            lt, st_ = rh + rs * buf / 100, rl - rs * buf / 100
            out += [("entry", "Long", 1, lt, None), ("entry", "Short", -1, st_, None),
                    ("exit", "ExL", "Long", rl + rs * slf, rh + rs * tpr), ("exit", "ExS", "Short", rh - rs * slf, rl - rs * tpr)]
        if S["done"]:
            out += [("cancel", "Long"), ("cancel", "Short")]
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate_ord(o, h, l, c, orders, log=log)
    ok, d = compare(run_conversion(TV_ID, df, tf="5", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(60000, seed=909, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 15000 * (df[k] / 100) ** 0.12
    msgs, allok = [], True
    cases = (({"區間開始 (分鐘)": 45, "區間結束 (分鐘)": 30}, ("Asia/Taipei", 11 * 60 + 45, 13 * 60 + 30, 38.2, 0.618, 0.1)),
             ({"圖表顯示時區": "America/New_York", "區間開始 (小時)": 8, "區間開始 (分鐘)": 0, "區進結束 (小時)": 9, "區間結束 (分鐘)": 0, "進場緩衝比例 (%)": 50.0, "止損位於區間水平": 0.3},
              ("America/New_York", 480, 540, 50.0, 0.618, 0.3)))
    for params, args in cases:
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
