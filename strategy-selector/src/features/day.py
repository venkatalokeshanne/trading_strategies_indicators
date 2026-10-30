"""Per symbol-day features at each checkpoint, using only information available at the checkpoint.
premarket = the 09:30 open: prior days' bars plus today's opening print (open of the 09:30 bar).
open+N   = also the bars of minutes [09:30, 09:30+N), i.e. only bars that closed before the checkpoint.
Pre-market volume / range need a Twelve Data Pro plan (RTH only here), so they are not produced."""
import numpy as np
import pandas as pd

from src.data.quality import load
from src.data.twelvedata import TZ

OPEN = 570        # 09:30 ET in minutes
OR_MIN = 5        # opening-range length for the ORB status
VOL_WIN = 20      # days for the volume baselines
MARKET = ["QQQ", "SPY"]
FEATS = ["gap_pct", "gap_atr", "prior_ret", "prior_range_pct", "prior_range_atr", "prior_close_pos", "prior_rel_vol",
         "range_pct", "range_atr", "ret", "ret_atr", "vol_rel", "vwap_dist", "orb"]


def _prep(b: pd.DataFrame) -> pd.DataFrame:
    et = b["time"].dt.tz_convert(TZ)
    return pd.DataFrame(dict(day=et.dt.normalize().dt.tz_localize(None), mins=et.dt.hour * 60 + et.dt.minute,
                             o=b["open"].to_numpy(), h=b["high"].to_numpy(), l=b["low"].to_numpy(),
                             c=b["close"].to_numpy(), v=b["volume"].to_numpy()))


def _prior(d: pd.DataFrame) -> pd.DataFrame:
    """Per-day stats from the day BEFORE (shifted), so day D never sees day D's own bars."""
    g = d.groupby("day")
    day = pd.DataFrame(dict(o=g["o"].first(), h=g["h"].max(), l=g["l"].min(), c=g["c"].last(), v=g["v"].sum()))
    pc = day["c"].shift(1)
    tr = pd.concat([day["h"] - day["l"], (day["h"] - pc).abs(), (day["l"] - pc).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    out = pd.DataFrame(index=day.index)
    out["prev_close"] = day["c"].shift(1)
    out["atr"] = atr.shift(1)
    out["prior_ret"] = day["c"].shift(1) / day["c"].shift(2) - 1
    out["prior_range_pct"] = ((day["h"] - day["l"]) / day["c"]).shift(1)
    out["prior_range_atr"] = ((day["h"] - day["l"]) / atr).shift(1)
    out["prior_close_pos"] = ((day["c"] - day["l"]) / (day["h"] - day["l"]).replace(0, np.nan)).shift(1)
    out["prior_rel_vol"] = (day["v"] / day["v"].rolling(VOL_WIN, min_periods=5).mean().shift(1)).shift(1)
    return out


def _window(d: pd.DataFrame, n: int) -> pd.DataFrame:
    w = d[(d["mins"] >= OPEN) & (d["mins"] < OPEN + n)]
    g = w.groupby("day")
    tp = (w["h"] + w["l"] + w["c"]) / 3
    r = pd.DataFrame(dict(hi=g["h"].max(), lo=g["l"].min(), last=g["c"].last(), vol=g["v"].sum(), open0=g["o"].first(),
                          pv=(tp * w["v"]).groupby(w["day"]).sum()))
    orw = w[w["mins"] < OPEN + OR_MIN].groupby("day")
    r["or_hi"], r["or_lo"] = orw["h"].max(), orw["l"].min()
    base = r["vol"].rolling(VOL_WIN, min_periods=5).mean().shift(1)     # same window on earlier days only
    r["vol_rel"] = r["vol"] / base
    return r


def day_features(bars: pd.DataFrame, checkpoint: str) -> pd.DataFrame:
    """One row per trading day with FEATS columns (NaN where the inputs are not available)."""
    d = _prep(bars)
    p = _prior(d)
    first = d.groupby("day").first()
    out = pd.DataFrame(index=p.index)
    open0 = first["o"].where(first["mins"] == OPEN)                      # opening print only if the 09:30 bar exists
    out["gap_pct"] = open0 / p["prev_close"] - 1
    out["gap_atr"] = (open0 - p["prev_close"]) / p["atr"]
    for k in ("prior_ret", "prior_range_pct", "prior_range_atr", "prior_close_pos", "prior_rel_vol"):
        out[k] = p[k]
    if checkpoint != "premarket":
        n = int(checkpoint.split("+")[1])
        w = _window(d, n).reindex(p.index)
        out["range_pct"] = (w["hi"] - w["lo"]) / w["open0"]
        out["range_atr"] = (w["hi"] - w["lo"]) / p["atr"]
        out["ret"] = w["last"] / w["open0"] - 1
        out["ret_atr"] = (w["last"] - w["open0"]) / p["atr"]
        out["vol_rel"] = w["vol_rel"]
        vwap = w["pv"] / w["vol"].replace(0, np.nan)
        out["vwap_dist"] = w["last"] / vwap - 1
        out["orb"] = np.where(n <= OR_MIN, 0.0, np.where(w["last"] > w["or_hi"], 1.0, np.where(w["last"] < w["or_lo"], -1.0, 0.0)))
        out.loc[w["last"].isna(), "orb"] = np.nan
    for f in FEATS:
        if f not in out:
            out[f] = np.nan
    out.index.name = "day"
    return out[FEATS]


def build(cfg, symbols, checkpoints=None) -> pd.DataFrame:
    """Long table: symbol, day, checkpoint, FEATS, mkt_gap_pct, mkt_ret, mkt_range_atr (market proxy = SPY if cached else QQQ)."""
    checkpoints = checkpoints or cfg["checkpoints"]
    from src.data.twelvedata import _dir
    mk = next((m for m in MARKET if (_dir(cfg, m) / "coverage.json").exists()), None)
    mbars = load(cfg, mk) if mk else None
    rows = []
    for cp in checkpoints:
        m = day_features(mbars, cp) if mbars is not None else None
        for s in symbols:
            b = load(cfg, s)
            if b.empty:
                continue
            f = day_features(b, cp)
            if m is not None:
                f["mkt_gap_pct"], f["mkt_ret"], f["mkt_range_atr"] = (m["gap_pct"].reindex(f.index), m["ret"].reindex(f.index), m["range_atr"].reindex(f.index))
            f.insert(0, "checkpoint", cp)
            f.insert(0, "symbol", s)
            rows.append(f.reset_index())
    return pd.concat(rows, ignore_index=True)
