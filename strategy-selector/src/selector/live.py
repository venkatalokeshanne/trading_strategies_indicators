"""Daily picks: market conditions -> strategy set, open conditions -> stocks. Trained only on days < asof."""
import json
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from src import config
from src.data import twelvedata as td
from src.data.quality import load
from src.features import day as F
from src.features import regimes as RG
from src.store import db

GATE, CHECKPOINT, TOPN, MIN_N, W_IN = "open+10", "open+10", 3, 30, 0.6
SF = ["range_pct", "vol_rel", "gap_pct", "prior_range_pct", "prior_rel_vol", "ret"]   # open+10 stock features (gap/ret used as absolute values)
STOP_PCT = 0.01


def learn_symbols(cfg) -> list[str]:
    c = pd.read_csv(cfg["paths"]["cache"].parent / "coverage.csv")
    return c[c["learn"]]["symbol"].tolist()


def member(R: pd.DataFrame) -> pd.DataFrame:
    """Long (symbol, date, regime) for regime weight >= W_IN."""
    m = R.rename(columns={"day": "date"}).melt(id_vars=["symbol", "date"], value_vars=RG.REGIMES, var_name="regime", value_name="w")
    return m[m["w"] >= W_IN][["symbol", "date", "regime"]]


def train_map(L: pd.DataFrame, M: pd.DataFrame, asof) -> dict[str, list[str]]:
    """regime -> TOPN variants with the best mean/std of pnl per symbol-day of that regime (consistency, not just average), rows strictly before asof."""
    a = pd.Timestamp(asof)
    L, M = L[L["date"] < a], M[M["date"] < a]
    n = M.groupby("regime").size()
    j = L.merge(M, on=["symbol", "date"]).assign(q=lambda x: x["pnl"] ** 2)
    s = j.groupby(["regime", "variant"])[["pnl", "q"]].sum().reset_index()
    nn = s["regime"].map(n)
    s["avg"] = s["pnl"] / nn
    s["score"] = s["avg"] / np.sqrt((s["q"] / nn - s["avg"] ** 2).clip(lower=1e-9))
    s = s[nn >= MIN_N].sort_values("score", ascending=False)
    s = s.assign(sid=s["variant"].str.split("|").str[0]).drop_duplicates(["regime", "sid"])   # best timeframe of each strategy: three different strategies, not one script at 5/10/15m
    return s.groupby("regime").head(TOPN).groupby("regime")["variant"].apply(list).to_dict()


def vote(sets: dict, regimes: list[str]) -> list[str]:
    c = pd.Series([v for r in regimes for v in sets.get(r, [])]).value_counts()
    return c[~c.index.str.split("|").str[0].duplicated()].head(TOPN).index.tolist()


def _x(f: pd.DataFrame) -> pd.DataFrame:
    g = f.assign(gap_pct=f["gap_pct"].abs(), ret=f["ret"].abs()).copy()
    return g.groupby("date")[SF].rank(pct=True).fillna(0.5).assign(b=1.0)


def fit_stocks(sd: pd.DataFrame, feat: pd.DataFrame, lam: float = 5.0) -> np.ndarray:
    d = sd.merge(feat, on=["symbol", "date"])
    X = _x(d).values
    return np.linalg.solve(X.T @ X + lam * np.eye(X.shape[1]), X.T @ d["p"].values)


def train(cfg, asof) -> dict:
    con = db.connect(cfg, read_only=True)
    a = pd.Timestamp(asof)
    syms = learn_symbols(cfg)
    L = con.execute("""SELECT d.variant, d.symbol, d.date, d.pnl FROM daily_pnl d JOIN variants v USING(variant)
                       WHERE v.status='ok' AND d.gate=? AND d.date < ?""", [GATE, a.date()]).df()
    L = L[L["symbol"].isin(syms)]
    L["date"] = pd.to_datetime(L["date"])
    days = pd.DatetimeIndex(sorted(L["date"].unique()))
    M = member(RG.regimes(cfg, syms, days))
    sets = train_map(L, M, a)
    # in-sample set pnl per past symbol-day (what the stock model learns to rank)
    pn = L.set_index(["variant", "symbol", "date"])["pnl"]
    rows = []
    for (s, d), rs in M.groupby(["symbol", "date"])["regime"]:
        vs = vote(sets, rs.tolist())
        if vs:
            rows.append((s, d, float(np.mean([pn.get((v, s, d), 0.0) for v in vs]))))
    sd = pd.DataFrame(rows, columns=["symbol", "date", "p"])
    feat = con.execute("SELECT * FROM features WHERE checkpoint=? AND day < ?", [CHECKPOINT, a.date()]).df().rename(columns={"day": "date"})
    feat["date"] = pd.to_datetime(feat["date"])
    return dict(sets=sets, w=fit_stocks(sd, feat), n_days=len(days), symbols=syms)


def fetch_today(cfg, symbols, day: str) -> None:
    """Catch the cache up to yesterday, then add today's bars so far (today is never marked covered)."""
    import os
    keys = td.Keys([k for k in os.environ.get("TWELVEDATA_API_KEYS", "").split(",") if k.strip()])
    for s in symbols:
        td.fetch_symbol(cfg, keys, s, (date.fromisoformat(day) - timedelta(days=10)).isoformat(), day)
        if date.fromisoformat(day) >= date.today():
            df = td.fetch_range(keys, s, f"{day} 09:30:00", f"{day} 16:00:00", False, cfg["data"]["outputsize"])
            td._store(td._dir(cfg, s), df)


def picks(cfg, asof: str, k: int = 2, model: dict | None = None) -> dict:
    a = pd.Timestamp(asof)
    m = model or train(cfg, asof)
    syms = m["symbols"]
    f = []
    for s in syms:
        b = load(cfg, s)
        if b.empty:
            continue
        r = F.day_features(b, CHECKPOINT)
        r.index = pd.to_datetime(r.index)
        if a in r.index and not np.isnan(r.loc[a, "range_pct"]):
            f.append(r.loc[[a]].assign(symbol=s))
    if not f:
        raise SystemExit(f"no {CHECKPOINT} bars for {asof}: fetch first (`cli picks --fetch`) and run after 09:40 ET")
    feat = pd.concat(f).rename_axis("date").reset_index()
    reg = member(RG.regimes(cfg, [s for s in feat["symbol"]], pd.DatetimeIndex([a])))
    feat["score"] = _x(feat).values @ m["w"]
    cat = {r["id"]: r["title"] for r in json.loads(cfg["paths"]["catalog"].read_text())}
    out = []
    for r in feat.sort_values("score", ascending=False).itertuples():
        rs = reg[reg["symbol"] == r.symbol]["regime"].tolist()
        vs = vote(m["sets"], rs)
        if vs:
            out.append(dict(symbol=r.symbol, score=round(float(r.score), 2), regimes=rs, strategies=[f"{v.split('|')[0]} {v.split('|')[1]} {cat.get(v.split('|')[0], '')}" for v in vs], variants=vs))
        if len(out) == k:
            break
    res = dict(date=asof, checkpoint=CHECKPOINT, k=k, stop_pct=STOP_PCT, trained_days=m["n_days"], picks=out)
    p = cfg["paths"]["runs"] / "live"
    p.mkdir(parents=True, exist_ok=True)
    (p / f"{asof}.json").write_text(json.dumps(res, indent=1))
    return res


def realised(cfg, res: dict) -> float | None:
    """P&L the picked symbols' strategy sets made that day in the store (None if the day isn't stored): a check, not part of the pick."""
    con = db.connect(cfg, read_only=True)
    tot, seen = 0.0, False
    for p in res["picks"]:
        r = con.execute("SELECT variant, pnl FROM daily_pnl WHERE symbol=? AND date=? AND gate=?", [p["symbol"], res["date"], GATE]).df()
        seen |= not r.empty
        tot += float(r[r["variant"].isin(p["variants"])]["pnl"].sum()) / len(p["variants"])
    return tot if seen else None
