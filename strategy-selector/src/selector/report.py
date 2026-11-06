"""One-page report of a backtest run (runs/<id>/) plus strategy-library health; compare two runs."""
import json

import numpy as np
import pandas as pd

from src.features import regimes as RG
from src.selector import bulk
from src.store import db


def resolve(cfg, run_id: str):
    root = cfg["paths"]["runs"]
    if run_id == "latest":
        run_id = sorted(p.name for p in root.iterdir() if p.is_dir() and (p / "summary.json").exists())[-1]
    d = root / run_id
    if not (d / "summary.json").exists():
        raise SystemExit(f"no run {run_id!r} in {root}")
    return d


def contributions(cfg, d) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Net $ of the traded picks by strategy and by dominant regime of the pick's symbol-day."""
    pk = pd.read_csv(d / "picks.csv", parse_dates=["day"])
    t = pk[pk["variant"] != "ABSTAIN"].copy()
    t["strategy"] = t["variant"].str.split("|").str[0]
    st = t.groupby("strategy").agg(picks=("pnl", "size"), net=("pnl", "sum"), win=("pnl", lambda x: (x > 0).mean())).sort_values("net", ascending=False)
    days = pd.DatetimeIndex(sorted(pk["day"].unique()))
    rg = RG.regimes(cfg, sorted(t["symbol"].unique()), days).set_index(["symbol", "day"])[RG.REGIMES].fillna(0.5)
    t["regime"] = [RG.REGIMES[int(np.argmax(rg.loc[(r.symbol, r.day)].to_numpy()))] for r in t.itertuples()]
    rt = t.groupby("regime").agg(picks=("pnl", "size"), net=("pnl", "sum"), win=("pnl", lambda x: (x > 0).mean())).sort_values("net", ascending=False)
    return st, rt


def library_health(cfg) -> dict:
    con = db.connect(cfg, read_only=True)
    v = con.execute("SELECT status, count(*) FROM variants GROUP BY 1").fetchall()
    r = con.execute("SELECT status, count(*), round(median(secs), 2) FROM runs GROUP BY 1").fetchall()
    per = con.execute("""SELECT split_part(variant, '|', 1) s, sum(n_trades) trades, count(*) FILTER (WHERE status='error') errors
                         FROM runs GROUP BY 1 ORDER BY trades""").df()
    silent = per[per["trades"] == 0]["s"].tolist()
    return dict(converted_full=len(bulk.converted_strategies()), in_store=int(per.shape[0]), variants=dict(v), jobs={a: (b, c) for a, b, c in r},
                never_traded=silent, with_errors=per[per["errors"] > 0]["s"].tolist())


def render(cfg, run_id: str, vs: str | None = None) -> str:
    d = resolve(cfg, run_id)
    s = json.loads((d / "summary.json").read_text())
    a = s["selector"]
    st, rt = contributions(cfg, d)
    h = library_health(cfg)
    L = [f"REPORT {d.name}: {s['window']} {s['checkpoint']} top_k={s['top_k']} {s['universe']}",
         f"net ${a['net']:+.0f} ({a['ret_pct']:+.2f}% of ${s['alloc']:.0f}), sharpe-like {a['sharpe']}, maxDD ${a['max_dd']:.0f}, win {s['win_rate']:.0%}/{s['trades']} trades, traded {a['days_traded']:.0%} of {s['test_days']} days, abstained {s['abstained']}/{s['picks']}",
         "baselines: " + "; ".join(f"{n.split(' (')[0].split(',')[0]} ${b['net']:+.0f}" for n, b in s["baselines"].items()),
         "by strategy (net $, picks, win): " + ", ".join(f"{i} {r.net:+.0f} ({r.picks:.0f}, {r.win:.0%})" for i, r in st.iterrows()),
         "by dominant regime: " + ", ".join(f"{i} {r.net:+.0f} ({r.picks:.0f})" for i, r in rt.iterrows()),
         f"library: {h['converted_full']} converted FULL, {h['in_store']} in store, variants {h['variants']}, jobs {h['jobs']} (status: n, median s); never traded: {h['never_traded'] or 'none'}; with errors: {h['with_errors'] or 'none'}",
         "bias: " + s["notes"][0]]
    if vs:
        o = json.loads((resolve(cfg, vs) / "summary.json").read_text())["selector"]
        L.append(f"vs {vs}: net {a['net'] - o['net']:+.0f}, sharpe {a['sharpe'] - o['sharpe']:+.2f}, maxDD {a['max_dd'] - o['max_dd']:+.0f} (this minus other; other: ${o['net']:+.0f}, sharpe {o['sharpe']})")
    return "\n".join(L)
