"""Stock ranker ("in play"): at a checkpoint pick the top K symbols of the day by a walk-forward ridge score.
Inputs per symbol-day are cross-sectional percentile ranks of features known at the checkpoint (|gap|, early volume, early range, prior-day activity, event)
plus the symbol's trailing tradeability. Target = the best variant's PnL of that symbol-day (from the bulk store). A day D is scored with a model fitted
only on days < D (day D-1's PnL is known at D's open); the baseline ranks by |gap| x relative volume."""
import numpy as np
import pandas as pd

FEATS = ["abs_gap", "vol_rel", "range_atr", "prior_rel_vol", "prior_range_atr", "event", "trade_hist"]
HIST = 20          # days of the symbol's own best-variant PnL in the tradeability term
RIDGE = 5.0


def target(cfg, gate: str) -> pd.DataFrame:
    """symbol-day best-variant PnL (0 for days with no trade), columns symbol, day, y."""
    from src.data import calendar
    from src.store import db
    con = db.connect(cfg, read_only=True)
    best = con.execute("""SELECT d.symbol, d.date AS day, max(d.pnl) AS y FROM daily_pnl d JOIN variants v USING (variant)
                          WHERE v.status='ok' AND d.gate = ? GROUP BY 1, 2""", [gate]).df()
    runs = con.execute("SELECT symbol, min(d0) d0, max(d1) d1 FROM runs WHERE gate = ? AND status='ok' GROUP BY 1", [gate]).df()
    rows = []
    for r in runs.itertuples():
        days = pd.DatetimeIndex(calendar.sessions(r.d0, r.d1)["day"])
        rows.append(pd.DataFrame(dict(symbol=r.symbol, day=days)))
    grid = pd.concat(rows)
    best["day"] = pd.to_datetime(best["day"])
    out = grid.merge(best, on=["symbol", "day"], how="left").fillna({"y": 0.0})
    return out


def design(feat: pd.DataFrame, ev: pd.DataFrame, y: pd.DataFrame) -> pd.DataFrame:
    """Rows symbol-day with FEATS (percentile ranks within the day) and y; `base` = |gap| x vol_rel for the baseline."""
    f = feat.copy()
    f["day"] = pd.to_datetime(f["day"])
    f = f.merge(y, on=["symbol", "day"], how="inner")
    e = ev[["symbol", "day", "fomc", "cpi", "jobs", "earn_reaction"]].copy()
    e["day"] = pd.to_datetime(e["day"])
    f = f.merge(e, on=["symbol", "day"], how="left")
    f["event"] = f[["fomc", "cpi", "jobs", "earn_reaction"]].fillna(0).max(axis=1)
    f = f.sort_values(["symbol", "day"])
    f["trade_hist"] = f.groupby("symbol")["y"].transform(lambda s: s.shift(1).rolling(HIST, min_periods=5).mean())   # PnL up to D-1 only
    f["abs_gap"] = f["gap_atr"].abs()
    f["base"] = f["abs_gap"] * f["vol_rel"]
    cols = [c for c in FEATS if c != "event"]
    f[cols] = f.groupby("day")[cols].rank(pct=True)
    f[FEATS] = f[FEATS].fillna(0.5)
    return f.dropna(subset=["abs_gap", "y"]).sort_values(["day", "symbol"]).reset_index(drop=True)


def _fit(X, y):
    mu = X.mean(0)
    Xc = X - mu
    w = np.linalg.solve(Xc.T @ Xc + RIDGE * len(X) / 100 * np.eye(X.shape[1]), Xc.T @ (y - y.mean()))
    return mu, w


def walk_forward(d: pd.DataFrame, k: int = 3, min_days: int = 60, refit_every: int = 5, feats: list[str] | None = None) -> pd.DataFrame:
    """Per test day: mean y of the model's top K, the baseline's top K, the tradeability-only top K, all symbols (= random pick in expectation) and the oracle top K."""
    feats = feats or FEATS
    d = d.copy()
    d["yr"] = d.groupby("day")["y"].rank(pct=True)          # percentile target: robust to a few huge days
    days = sorted(d["day"].unique())
    out, model = [], None
    for n, day in enumerate(days):
        if n < min_days:
            continue
        today = d[d["day"] == day]
        if model is None or (n - min_days) % refit_every == 0:
            h = d[d["day"] < day]
            model = _fit(h[feats].to_numpy(), h["yr"].to_numpy())
        s = (today[feats].to_numpy() - model[0]) @ model[1]
        top = lambda score: today.iloc[np.argsort(-score)[:k]]["y"].mean()
        out.append(dict(day=day, picks=today.iloc[np.argsort(-s)[:k]]["symbol"].tolist(), model=top(s), base=top(today["base"].to_numpy()), hist=top(today["trade_hist"].to_numpy()), rand=today["y"].mean(),
                        oracle=today.nlargest(k, "y")["y"].mean(), n=len(today)))
    return pd.DataFrame(out)


def evaluate(r: pd.DataFrame, seed: int = 0, boots: int = 2000) -> dict:
    """Mean daily y per picker and the model-minus-X paired difference with a bootstrap 95% interval over days."""
    rng = np.random.default_rng(seed)
    res = {"days": len(r), **{c: round(float(r[c].mean()), 2) for c in ("model", "base", "hist", "rand", "oracle")}}
    for ref in ("base", "hist", "rand"):
        diff = (r["model"] - r[ref]).to_numpy()
        bs = [diff[rng.integers(0, len(diff), len(diff))].mean() for _ in range(boots)]
        res[f"model-{ref}"] = (round(float(diff.mean()), 2), tuple(np.round(np.percentile(bs, [2.5, 97.5]), 2)))
    return res
