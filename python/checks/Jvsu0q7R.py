"""Independent check — Gemini Scalper V1 (Jvsu0q7R): EMA50/200 cross reversal. Both exits are
re-placed every bar from the position's average price at that close (na when flat), so on
bar i the bracket comes from the average price at the close of bar i-1 — which after a
reversal is the previous position's price."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, np_rsi, run_conversion, simulate

TV_ID = "Jvsu0q7R"


def check():
    df = bars(3000, seed=59)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    f, s, rsi = np_ema(c, 50), np_ema(c, 200), np_rsi(c, 14)
    buy = np_cross_over(f, s) & (rsi < 70)
    sell = np_cross_under(f, s) & (rsi > 30)
    avg_end = np.full(len(c), np.nan)
    cur = {"ep": np.nan}

    def orders(i, pos):
        avg_end[i] = cur["ep"] if pos else np.nan
        return ([("entry", 1)] if buy[i] else []) + ([("entry", -1)] if sell[i] else [])

    def stop(i, pos, ep, eb):
        cur["ep"] = ep
        a = avg_end[i - 1]
        return None if np.isnan(a) else a * (0.995 if pos > 0 else 1.005)

    def target(i, pos, ep, eb):
        a = avg_end[i - 1]
        return None if np.isnan(a) else a * (1.01 if pos > 0 else 0.99)

    ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    return compare(run_conversion(TV_ID, df), ref)
