"""Independent check — anh Manh dep trai (x8rkJOjn): stop multiplied by (1+M) every bar in a position."""
import numpy as np
from indep import bars, compare, np_sma, run_conversion, simulate


def check():
    df = bars(3000, seed=28)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    avg = np_sma((o + l) / 2, 5)
    n = len(c)
    # what the Pine script holds at each bar's close; the exit placed then works on the NEXT bar
    state = {"count": 0, "stop": np.nan, "level": [np.nan] * (n + 1)}

    def orders(i, pos):
        state["count"] = state["count"] + 1 if o[i] < c[i] else 0
        out = []
        if state["count"] == 3 and pos == 0:
            out.append(("entry", 1))
            state["stop"] = avg[i]
        if pos > 0:
            state["stop"] = state["stop"] * 2.0
        state["level"][i + 1] = state["stop"] if pos > 0 else np.nan
        return out

    def stop(i, pos, ep, eb):
        v = state["level"][i]
        return None if v != v else v
    return compare(run_conversion("x8rkJOjn", df), simulate(o, h, l, c, orders, stop=stop))
