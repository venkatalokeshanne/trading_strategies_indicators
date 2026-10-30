"""Walk-forward backtest: for each day in [from, to] rank stocks -> pick a variant per stock (or abstain) -> take that variant's gated per-day trades
from the bulk store (costs already inside) -> aggregate. Everything learned for day D uses only days < D."""
import json
import time
from datetime import datetime

import numpy as np
import pandas as pd

from src import config
from src.selector import ranker, variant
from src.store import db

NOTES = ["Watchlists were curated today from stocks that already moved (hindsight bias): results are optimistic; --neutral reruns on QQQ + mega-caps.",
         "Variants are the converted strategies in the store only; Twelve Data bars are not TradingView bars; RTH only (no pre-market).",
         "Costs are guesses by liquidity tier; 'best single variant' baseline is chosen in-sample (optimistic)."]


def _stats(daily: pd.Series, alloc: float) -> dict:
    eq = daily.cumsum()
    dd = (eq - eq.cummax()).min()
    sd = daily.std()
    return dict(net=round(float(daily.sum()), 1), ret_pct=round(100 * float(daily.sum()) / alloc, 2),
                sharpe=round(float(daily.mean() / sd * np.sqrt(252)), 2) if sd and sd > 0 else 0.0,
                max_dd=round(float(dd), 1), max_dd_pct=round(100 * float(dd) / alloc, 2), days_traded=round(float((daily != 0).mean()), 2))


def run(cfg, d_from: str, d_to: str, checkpoint: str = "open+10", k: int = 3, neutral: bool = False, min_days: int = 60,
        min_sample: int = 20, threshold: float = 0.0, out_dir=None, detail: bool = False) -> dict:
    con = db.connect(cfg, read_only=True)
    cov = pd.read_csv(cfg["paths"]["cache"].parent / "coverage.csv").query("learn")["symbol"].tolist()
    if neutral:
        cov = [s for s in cov if s == "QQQ" or s in cfg["tiers"]["mega"]]
    feat = con.execute("SELECT * FROM features WHERE checkpoint = ?", [checkpoint]).df()
    d = ranker.design(feat[feat["symbol"].isin(cov)], con.execute("SELECT * FROM events").df(), ranker.target(cfg, checkpoint))
    d = d[d["symbol"].isin(cov)]
    all_days = sorted(d["day"].unique())
    test = [x for x in all_days if pd.Timestamp(d_from) <= x <= pd.Timestamp(d_to)]
    before = [x for x in all_days if x < pd.Timestamp(d_from)]
    if not test:
        raise SystemExit(f"no stored days in [{d_from}, {d_to}] (store covers {all_days[0].date()}..{all_days[-1].date()})")
    if len(before) < min_days:
        raise SystemExit(f"not enough history before {d_from}: {len(before)} stored days, need >= {min_days} (store starts {all_days[0].date()})")
    rk = ranker.walk_forward(d, k, min_days)
    rk = rk[rk["day"].isin(test)].reset_index(drop=True)
    r0, r1 = con.execute("SELECT min(d0), max(d1) FROM runs").fetchall()[0]
    dd, sy, vs, P, R = variant.load(cfg, checkpoint, cov, r0, r1)
    notional = cfg["adapter"]["notional"]
    picks, per_day, base = [], [], {b: [] for b in ("rank_only", "best_single", "random_expect", "oracle_variant")}
    for r in rk.itertuples():
        t = int(dd.get_loc(r.day))
        assert t > 0 and all(dd[:t] < r.day), "learning window must be strictly before the target day"
        day_pnl, rank_only, oracle = 0.0, 0.0, 0.0
        for s in r.picks:
            j = sy.index(s)
            res = variant.select(P, R, vs, t, j, min_sample, threshold)
            pnl = float(P[t, j, vs.index(res["pick"])]) if res["pick"] else 0.0
            day_pnl += pnl
            rank_only += float(P[t, j].mean())
            oracle += float(P[t, j].max())
            picks.append(dict(day=r.day.date(), symbol=s, variant=res["pick"] or "ABSTAIN", score=res["score"], n_sym=round(res["n_sym"], 1), n_reg=round(res["n_reg"], 1),
                              candidates=res["candidates"], pnl=pnl))
        per_day.append(dict(day=r.day, pnl=day_pnl))
        base["rank_only"].append(rank_only)
        base["oracle_variant"].append(oracle)
        base["random_expect"].append(k * float(P[t].mean()))                      # k random symbols x a random variant, in expectation
        base["best_single"].append([float(P[t, [sy.index(s) for s in r.picks]][:, v].sum()) for v in range(len(vs))])
    daily = pd.DataFrame(per_day).set_index("day")["pnl"]
    alloc = k * notional
    bs = np.array(base["best_single"])
    best_v = int(bs.sum(0).argmax())
    base_days = {"rank_only (equal-weight all variants on the ranked stocks)": pd.Series(base["rank_only"], index=daily.index),
                 f"best single variant, in-sample ({vs[best_v]})": pd.Series(bs[:, best_v], index=daily.index),
                 "random stocks+variant (expectation)": pd.Series(base["random_expect"], index=daily.index),
                 "oracle variant on ranked stocks (hindsight)": pd.Series(base["oracle_variant"], index=daily.index)}
    pk = pd.DataFrame(picks)
    traded = pk[pk["variant"] != "ABSTAIN"]
    tr = pd.DataFrame()
    if len(traded):
        con.register("p_", traded.assign(gate=checkpoint)[["variant", "symbol", "gate", "day"]])
        tr = con.execute("SELECT t.* FROM trades t JOIN p_ p ON t.variant = p.variant AND t.symbol = p.symbol AND t.gate = p.gate AND t.day = p.day").df()
    s = dict(window=f"{d_from}..{d_to}", checkpoint=checkpoint, top_k=k, universe="neutral (QQQ + mega-caps)" if neutral else f"{len(cov)} symbols",
             test_days=len(daily), picks=len(pk), abstained=int((pk["variant"] == "ABSTAIN").sum()), candidates_per_pick=18 if not pk.empty else 0,
             alloc=alloc, trades=len(tr), win_rate=round(float((tr["pnl"] > 0).mean()), 3) if len(tr) else 0.0, selector=_stats(daily, alloc),
             baselines={n: _stats(x, alloc) for n, x in base_days.items()}, notes=NOTES)
    out = (out_dir or cfg["paths"]["runs"] / datetime.now().strftime("%Y%m%d-%H%M%S")) if out_dir is not False else None
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        (out / "summary.json").write_text(json.dumps(s, indent=1, default=str))
        pd.DataFrame({"selector": daily, **{n.split(" ")[0]: x for n, x in base_days.items()}}).to_csv(out / "daily.csv")
        tr.to_csv(out / "trades.csv", index=False)
        pk.to_csv(out / "picks.csv", index=False)
        daily.cumsum().rename("equity").to_csv(out / "equity.csv")
        s["out"] = str(out)
    if detail:                                          # for the robustness tests (not serialised)
        s["_detail"] = dict(daily=daily, picks=pk, P=P, R=R, syms=sy, variants=vs, days=dd, test_idx=[int(dd.get_loc(x)) for x in daily.index])
    return s


def render(s: dict) -> str:
    a = s["selector"]
    L = [f"BACKTEST {s['window']} checkpoint={s['checkpoint']} top_k={s['top_k']} universe={s['universe']}",
         f"selector: net ${a['net']:+.0f} (after costs) = {a['ret_pct']:+.2f}% of ${s['alloc']:.0f} allocated | sharpe-like {a['sharpe']} | max DD ${a['max_dd']:.0f} ({a['max_dd_pct']}%) | win rate {s['win_rate']:.0%} over {s['trades']} trades",
         f"{s['test_days']} test days, {a['days_traded']:.0%} traded, {s['picks']} picks ({s['abstained']} abstained), {s['candidates_per_pick']} variants considered per pick"]
    for n, b in s["baselines"].items():
        L.append(f"  vs {n}: net ${b['net']:+.0f}, sharpe {b['sharpe']}, maxDD ${b['max_dd']:.0f}")
    L.append("bias: " + s["notes"][0])
    if "out" in s:
        L.append(f"files: {s['out']}")
    return "\n".join(L)
