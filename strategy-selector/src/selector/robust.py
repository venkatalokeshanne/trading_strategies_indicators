"""Robustness of the selector's backtest: costs x2, neutral universe, concentration, block bootstrap, shuffled-day test, threshold stability -> verdict."""
import json

import numpy as np
import pandas as pd

from src import config
from src.features import regimes as RG
from src.selector import backtest

THRESHOLDS = [-5.0, 0.0, 3.0, 6.0, 10.0]
X2_DB = "data/store_x2.duckdb"


def _block_boot(x: np.ndarray, block: int = 5, n: int = 2000, seed: int = 0):
    rng = np.random.default_rng(seed)
    m = len(x)
    starts = np.arange(0, m - block + 1)
    nb = int(np.ceil(m / block))
    tot = [np.concatenate([x[s:s + block] for s in rng.choice(starts, nb)])[:m].sum() for _ in range(n)]
    return np.percentile(tot, [2.5, 97.5])


def _shuffle(det, n: int = 1000, seed: int = 1):
    """Keep every traded (symbol, variant) pick but give it the PnL of a random OTHER day of the test window: a day-informed selector must beat this."""
    rng = np.random.default_rng(seed)
    P, vs, sy, days, ti = det["P"], det["variants"], det["syms"], det["days"], np.array(det["test_idx"])
    pk = det["picks"]
    pk = pk[pk["variant"] != "ABSTAIN"]
    j = np.array([sy.index(s) for s in pk["symbol"]])
    v = np.array([vs.index(x) for x in pk["variant"]])
    own = np.array([int(days.get_loc(pd.Timestamp(d))) for d in pk["day"]])
    actual = float(P[own, j, v].sum())
    sh = np.array([P[rng.choice(ti, len(pk)), j, v].sum() for _ in range(n)])
    return actual, float((sh >= actual).mean()), float(sh.mean())


def run(cfg, d_from: str, d_to: str, checkpoint: str = "open+10", k: int = 3, out=None) -> dict:
    kw = dict(checkpoint=checkpoint, k=k, out_dir=False)
    base = backtest.run(cfg, d_from, d_to, detail=True, **kw)
    det = base.pop("_detail")
    net = base["selector"]["net"]
    res = dict(window=base["window"], base_net=net, alloc=base["alloc"])
    x2 = None
    if (config.ROOT / X2_DB).exists():
        x2 = backtest.run(config.load(X2_DB, 2.0), d_from, d_to, **kw)["selector"]["net"]
    res["costs_x2_net"] = x2
    neu = backtest.run(cfg, d_from, d_to, neutral=True, **kw)
    res["neutral_net"] = neu["selector"]["net"]
    res["neutral_best_single_net"] = next(b for n, b in neu["baselines"].items() if n.startswith("best single"))["net"]
    pk = det["picks"]
    by_sym = pk.groupby("symbol")["pnl"].sum().sort_values(ascending=False)
    res["top3_symbol_share_of_gross_gain"] = round(float(by_sym.head(3).sum() / by_sym[by_sym > 0].sum()), 2) if (by_sym > 0).any() else None
    res["top_symbols"] = {s: round(float(x), 0) for s, x in by_sym.head(3).items()} | {s: round(float(x), 0) for s, x in by_sym.tail(2).items()}
    t_idx = {pd.Timestamp(d): i for i, d in enumerate(det["days"])}
    dom = []
    for r in pk.itertuples():
        dom.append(RG.REGIMES[int(np.argmax(det["R"][t_idx[pd.Timestamp(r.day)], det["syms"].index(r.symbol)]))])
    res["net_by_dominant_regime"] = {k_: round(float(v), 0) for k_, v in pk.assign(reg=dom).groupby("reg")["pnl"].sum().items()}
    lo, hi = _block_boot(det["daily"].to_numpy())
    res["bootstrap_net_ci95"] = [round(float(lo), 0), round(float(hi), 0)]
    actual, p, shmean = _shuffle(det)
    res["shuffle"] = dict(actual=round(actual, 0), shuffled_mean=round(shmean, 0), p_ge_actual=round(p, 3))
    res["threshold_net"] = {str(th): backtest.run(cfg, d_from, d_to, threshold=th, **kw)["selector"]["net"] for th in THRESHOLDS}
    checks = {"net>0": net > 0, "costs x2 net>0": bool(x2 is not None and x2 > 0), "neutral net>0": res["neutral_net"] > 0,
              "bootstrap CI above 0": lo > 0, "shuffled-day p<0.05": p < 0.05,
              "threshold stable (>=4/5 positive)": sum(v > 0 for v in res["threshold_net"].values()) >= 4}
    res["checks"] = checks
    res["verdict"] = "none" if (net <= 0 or p > 0.2) else "real" if all(checks.values()) else "fragile"
    res["why"] = [f"fails: {n}" for n, ok in checks.items() if not ok] or ["all checks pass"]
    if out is not None:
        out.write_text(json.dumps(res, indent=1, default=str))
    return res


def render(r: dict) -> str:
    L = [f"ROBUSTNESS {r['window']}  verdict: {r['verdict'].upper()}  ({'; '.join(r['why'])})",
         f"net ${r['base_net']:+.0f} on ${r['alloc']:.0f} | costs x2 ${r['costs_x2_net']} | neutral universe ${r['neutral_net']:+.0f} (its best single variant ${r['neutral_best_single_net']:+.0f})",
         f"bootstrap (5-day blocks) net 95% CI {r['bootstrap_net_ci95']} | shuffled-day: actual ${r['shuffle']['actual']:+.0f} vs shuffled mean ${r['shuffle']['shuffled_mean']:+.0f}, p(shuffled >= actual) = {r['shuffle']['p_ge_actual']}",
         f"threshold stability (net by $ threshold): {r['threshold_net']}",
         f"concentration: top-3 symbols = {r['top3_symbol_share_of_gross_gain']} of gross gains; top/bottom {r['top_symbols']}",
         f"net by dominant regime: {r['net_by_dominant_regime']}"]
    return "\n".join(L)
