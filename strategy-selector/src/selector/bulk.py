"""Bulk runner: every usable variant (strategy x tf x param set) x symbol x gate -> DuckDB. Resumable, process-parallel."""
import json
import os
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from pathlib import Path

import pandas as pd
import yaml

from src import config
from src.adapter import daytrade
from src.data.quality import load
from src.store import db

_bars: dict = {}


def converted_strategies() -> dict[str, Path]:
    """id -> script path for strategies the TV repo marks python FULL."""
    root = config.pine_repo()
    prog = json.loads((root / "progress/progress.json").read_text())["scripts"]
    out = {}
    for sid, v in prog.items():
        if v.get("type") == "strategy" and v.get("python_status") == "FULL":
            f = sorted((root / "python/strategies").glob(sid + "-*.py")) or sorted((root / "python/strategies").glob(sid + ".py"))
            if f:
                out[sid] = f[0]
    return out


def variants(cfg, ids: list[str] | None) -> list[dict]:
    """strategy x tf x param set; param sets come from config/variants.yaml (id -> {label: params}), default one empty set."""
    f = config.ROOT / "config/variants.yaml"
    psets = yaml.safe_load(f.read_text()) if f.exists() else {}
    scripts = converted_strategies()
    out = []
    for sid in (ids or sorted(scripts)):
        for tf in cfg["timeframes"]:
            for label, p in (psets.get(sid) or {"default": {}}).items():
                out.append(dict(variant=f"{sid}|{tf}m|{label}", strategy=sid, script=str(scripts[sid]), tf=tf, label=label, params=p or {}))
    return out


def _data(cfg, symbol):
    if symbol not in _bars:
        b = load(cfg, symbol)
        _bars[symbol] = (b, daytrade.data_hash(b))
    return _bars[symbol]


def job_key(cfg, v, symbol, gate, start, end) -> str:
    b, dh = _data(cfg, symbol)
    return daytrade.cache_key(cfg, v["script"], symbol, v["tf"], gate, start, end, v["params"], b, dh)


def _work(args):
    cfg, v, symbol, gate, start, end = args
    t0 = time.time()
    try:
        b, _ = _data(cfg, symbol)
        t = daytrade.run_day_trades(cfg, v["script"], symbol, v["tf"], gate, start, end, v["params"], b)
        return "ok", t, time.time() - t0, ""
    except Exception as e:                      # one broken script must not stop the bulk run
        return "error", None, time.time() - t0, f"{type(e).__name__}: {e}"


def plan(cfg, con, vs, symbols, gates, start, end) -> list[tuple]:
    done = {r[0] for r in con.execute("SELECT key FROM runs").fetchall()}
    return [(job_key(cfg, v, s, g, start, end), v, s, g) for v in vs for s in symbols for g in gates
            if job_key(cfg, v, s, g, start, end) not in done]


def estimate(con, todo, workers) -> tuple[float, float]:
    r = con.execute("SELECT median(secs) FROM runs WHERE status='ok'").fetchone()[0]
    per = r if r else 1.0
    return per, per * len(todo) / workers


def run(cfg, ids, symbols, gates, start, end, workers=None, max_minutes=30.0, yes=False, say=print) -> dict:
    workers = workers or os.cpu_count() or 1
    con = db.connect(cfg)
    vs = variants(cfg, ids)
    total = len(vs) * len(symbols) * len(gates)
    todo = plan(cfg, con, vs, symbols, gates, start, end)
    per, eta = estimate(con, todo, workers)
    say(f"variants={len(vs)} jobs={total} todo={len(todo)} workers={workers} ~{per:.1f}s/job -> est {eta / 60:.1f} min")
    if eta / 60 > max_minutes and not yes:
        say(f"estimate above {max_minutes:.0f} min: rerun with --yes to proceed")
        return dict(total=total, todo=len(todo), ran=0)
    vmap = {v["variant"]: v for v in vs}
    for v in vs:
        con.execute("INSERT OR IGNORE INTO variants VALUES (?,?,?,?,'ok','')", [v["variant"], v["strategy"], v["tf"], json.dumps(v["params"])])
    dead: set = set()
    probed: dict = {}
    d0, d1 = pd.Timestamp(start).date(), pd.Timestamp(end).date()
    it = iter(todo)
    ran = 0
    with ProcessPoolExecutor(workers) as ex:
        pend: dict = {}

        def feed():
            while len(pend) < workers * 3:
                nxt = next(it, None)
                if nxt is None:
                    return
                key, v, s, g = nxt
                if v["variant"] in dead:
                    continue
                pend[ex.submit(_work, (cfg, v, s, g, start, end))] = nxt

        feed()
        while pend:
            fin, _ = wait(pend, return_when=FIRST_COMPLETED)
            for fu in fin:
                key, v, s, g = pend.pop(fu)
                status, t, secs, err = fu.result()
                db.save_job(con, key, v["variant"], s, g, d0, d1, status, t, secs, err)
                ran += 1
                if status == "error":
                    probed[v["variant"]] = probed.get(v["variant"], 0) + 1
                    if probed[v["variant"]] >= 2:       # two failures: the script is broken, stop spending compute on it
                        dead.add(v["variant"])
            feed()
    mark_degenerate(con)
    say(f"ran={ran} runs={con.execute('SELECT count(*) FROM runs').fetchone()[0]} " +
        str(dict(con.execute("SELECT status, count(*) FROM variants GROUP BY 1").fetchall())))
    return dict(total=total, todo=len(todo), ran=ran)


def mark_degenerate(con) -> None:
    """A variant that errored on every job or never produced a trade is dropped from queries (status error / dead)."""
    con.execute("""UPDATE variants SET status = CASE WHEN r.ok = 0 THEN 'error' ELSE 'dead' END,
                       reason = CASE WHEN r.ok = 0 THEN 'every job failed' ELSE 'no trades on any symbol/gate' END
                   FROM (SELECT variant, count(*) FILTER (WHERE status='ok') ok, sum(n_trades) n FROM runs GROUP BY variant) r
                   WHERE variants.variant = r.variant AND (r.ok = 0 OR r.n = 0)""")
    con.execute("""UPDATE variants SET status='ok', reason='' FROM (SELECT variant, sum(n_trades) n FROM runs GROUP BY variant) r
                   WHERE variants.variant = r.variant AND variants.status <> 'ok' AND r.n > 0""")


def top_bottom(cfg, day: str, n: int = 5, gate: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Best / worst live variants on one day by total pnl over symbols (only variants that traded that day)."""
    con = db.connect(cfg, read_only=True)
    q = """SELECT d.variant, d.gate, round(sum(d.pnl), 2) pnl, sum(d.n_trades) trades, count(DISTINCT d.symbol) symbols
           FROM daily_pnl d JOIN variants v USING (variant) WHERE v.status='ok' AND d.date = ? {g}
           GROUP BY d.variant, d.gate ORDER BY pnl {o} LIMIT ?"""
    args = [day] + ([gate] if gate else [])
    g = "AND d.gate = ?" if gate else ""
    return (con.execute(q.format(g=g, o="DESC"), args + [n]).df(), con.execute(q.format(g=g, o="ASC"), args + [n]).df())
