"""Per symbol-day data checks over cached 1-min bars. Flags bad days, never deletes bars."""
import json

import pandas as pd

from src.data import calendar
from src.data.twelvedata import TZ, _dir

MISSING_FRAC = 0.02      # >2% of the session's minutes missing
JUMP = 0.25              # one-minute |close/prev close - 1|
GAP = 0.40               # overnight |open/prev close - 1| (split-like)


def load(cfg, sym) -> pd.DataFrame:
    fs = sorted(_dir(cfg, sym).glob("*.parquet"))
    return pd.concat(pd.read_parquet(f) for f in fs) if fs else pd.DataFrame()


def check_symbol(cfg, sym) -> tuple[pd.DataFrame, dict]:
    """Returns (per-day table with flags, symbol summary). Only days in coverage.json are judged."""
    d = _dir(cfg, sym)
    cov = sorted(json.loads((d / "coverage.json").read_text())) if (d / "coverage.json").exists() else []
    bars = load(cfg, sym)
    if not cov or bars.empty:
        return pd.DataFrame(), dict(symbol=sym, first=None, last=None, days=0, no_data=0, bad=0, learn=False)
    ses = calendar.sessions(cov[0], cov[-1])
    bars = bars.sort_values("time")
    bars["day"] = bars["time"].dt.tz_convert(TZ).dt.date
    # days before the first bar are pre-listing, not data errors
    ses = ses[ses["day"].astype(str).isin(set(cov)) & (ses["day"] >= bars["day"].iloc[0])]
    g = bars.groupby("day")
    bars["ret"] = g["close"].pct_change().abs()      # within-day only; overnight is `gap`
    g = bars.groupby("day")
    day = pd.DataFrame({"n": g.size(), "dups": g["time"].apply(lambda t: t.duplicated().sum()),
                        "vol": g["volume"].sum(), "zero_vol": g["volume"].apply(lambda v: (v == 0).sum()),
                        "jump": g["ret"].max(), "o": g["open"].first(), "c": g["close"].last()})
    day["gap"] = (day["o"] / day["c"].shift() - 1).abs()
    day["outside"] = bars.merge(ses, on="day", how="left").assign(
        out=lambda m: (m["time"] < m["s_open"]) | (m["time"] >= m["s_close"])).groupby("day")["out"].sum()
    t = ses.set_index("day").join(day)
    t["expected"] = ((t["s_close"] - t["s_open"]).dt.total_seconds() // 60).astype(int)
    t["n"] = t["n"].fillna(0).astype(int)
    t["missing"] = (t["expected"] - (t["n"] - t["outside"].fillna(0))).clip(lower=0)
    t["flags"] = [",".join(f for f, on in [
        ("no_data", r.n == 0), ("missing", r.n > 0 and r.missing > MISSING_FRAC * r.expected),
        ("zero_volume", r.n > 0 and r.vol == 0), ("dups", r.dups > 0), ("outside", r.outside > 0),
        ("jump", r.jump > JUMP), ("gap", r.gap > GAP)] if on) for r in t.itertuples()]
    t["bad"] = t["flags"] != ""
    t.insert(0, "symbol", sym)
    ok = int((t["n"] > 0).sum())
    s = dict(symbol=sym, first=str(t.index.min()), last=str(t.index.max()), days=ok,
             no_data=int((t["n"] == 0).sum()), bad=int(t["bad"].sum()),
             learn=ok >= cfg["min_history_days"])
    return t.reset_index()[["symbol", "day", "expected", "n", "missing", "flags", "bad"]], s
