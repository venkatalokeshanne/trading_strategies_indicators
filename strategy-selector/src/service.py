"""Plain functions for a future UI/API: dicts and DataFrames only. The CLI calls these same functions."""
import json

import pandas as pd

from src import config
from src.features import regimes
from src.selector import backtest, report
from src.store import db


def run_backtest(d_from: str, d_to: str, checkpoint: str = "open+10", top_k: int = 3, neutral: bool = False) -> dict:
    """Run and store a walk-forward backtest; returns the summary dict (includes `out`, the run directory)."""
    return backtest.run(config.load(), d_from, d_to, checkpoint, top_k, neutral)


def list_runs() -> pd.DataFrame:
    """One row per stored run: id, window, checkpoint, top_k, universe, net, sharpe, max_dd."""
    root = config.load()["paths"]["runs"]
    rows = []
    for p in sorted(root.iterdir()) if root.exists() else []:
        if (p / "summary.json").exists():
            s = json.loads((p / "summary.json").read_text())
            rows.append(dict(run_id=p.name, window=s["window"], checkpoint=s["checkpoint"], top_k=s["top_k"], universe=s["universe"],
                             net=s["selector"]["net"], sharpe=s["selector"]["sharpe"], max_dd=s["selector"]["max_dd"]))
    return pd.DataFrame(rows, columns=["run_id", "window", "checkpoint", "top_k", "universe", "net", "sharpe", "max_dd"])


def get_run(run_id: str = "latest") -> dict:
    """summary (dict) and daily / picks / trades / equity (DataFrames) of one run."""
    d = report.resolve(config.load(), run_id)
    return dict(run_id=d.name, summary=json.loads((d / "summary.json").read_text()),
                **{k: pd.read_csv(d / f"{k}.csv") for k in ("daily", "picks", "trades", "equity")})


def get_variant_stats(gate: str = "open+10", day: str | None = None) -> pd.DataFrame:
    """Per variant: traded symbol-days, trades, net $ and win rate over the whole store (or on one `day`), best first. Dead/error variants excluded."""
    con = db.connect(config.load(), read_only=True)
    where = "AND t.day = ?" if day else ""
    q = f"""SELECT t.variant, count(DISTINCT (t.symbol, t.day)) symbol_days, count(*) trades, round(sum(t.pnl), 1) net, round(avg((t.pnl > 0)::INT), 3) win
            FROM trades t JOIN variants v USING (variant) WHERE v.status = 'ok' AND t.gate = ? {where} GROUP BY 1 ORDER BY net DESC"""
    return con.execute(q, [gate] + ([day] if day else [])).df()


def get_regime_table(day: str | None = None, top: int = 3, gate: str | None = None) -> pd.DataFrame:
    """With `day`: the 8 soft-regime weights of every stored symbol on that day. Without: per regime, symbol-days and the best variants' weighted mean daily $."""
    cfg = config.load()
    if day is None:
        return regimes.report(cfg, top, gate)
    syms = sorted(pd.read_csv(cfg["paths"]["cache"].parent / "coverage.csv").query("learn")["symbol"])
    r = regimes.regimes(cfg, syms, pd.DatetimeIndex([pd.Timestamp(day)]))
    return r.drop(columns="day").set_index("symbol").round(2)
