"""
The backtest pipeline: every converted strategy × symbol × timeframe.

  1. data is fetched (or read from cache) in the main process — providers are rate-limited
  2. each strategy is repaint-audited once, on its first combination with enough bars
  3. backtests run in parallel worker processes
  4. per strategy, "breadth" = share of its backtests that are profitable (evidence that
     the edge is not one lucky symbol); then quality gate + Robust Score; then stored.

    python -m tradesearch.pipeline --timeframes 60 240 D --workers 15
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

for _s in (sys.stdout, sys.stderr):           # LESSONS L8: cp1252 consoles
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import catalog, data, db, scoring

TIMEFRAMES = ("15", "60", "240", "D")


def _symbolinfo(ref_d: dict):
    from pinelib import SymbolInfo
    return SymbolInfo.make(ref_d["tickerid"], ref_d["type"], description=ref_d.get("description", ""),
                           currency=ref_d.get("currency", "USD"), basecurrency=ref_d.get("base_currency", ""))


def job(args: tuple) -> dict:
    """One backtest (+ optionally the strategy's repaint audit). Runs in a worker process."""
    path, ref_d, tf, params, n_bars, do_audit, pine_path = args
    t0 = time.perf_counter()
    try:
        from pinelib import metrics, run, tf_seconds
        ref = data.SymbolRef(**ref_d)
        bars = data.load_cached(ref, tf)
        if bars is None or len(bars) < 50:
            return {"ok": False, "path": path, "tickerid": ref.tickerid, "tf": tf, "error": "no data"}
        bars = bars.tail(n_bars).reset_index(drop=True)
        cls = catalog.load_script(Path(path))
        sym = _symbolinfo(ref_d)
        res = run(cls, bars, params=params, symbol=sym, timeframe=tf,
                  data_provider=data.provider_for_scripts(n_bars))
        m = metrics.compute(res)
        trades = metrics.trades_table(res)
        curves = metrics.curves(res, points=1500)
        monthly = metrics._monthly_returns(res.bars["time"].to_numpy(), res.broker.equity_close, sym.timezone)
        out = {"ok": True, "path": path, "tickerid": ref.tickerid, "tf": tf, "params": params or {},
               "inputs": res.inputs, "bars": len(bars), "metrics": m, "trades": trades,
               "curves": curves, "monthly": monthly,
               "strategy_type": catalog.classify_holding(m.get("avgBarsInTrade"), tf_seconds(tf))}
        if do_audit:
            from . import repaint
            src = Path(pine_path).read_text(encoding="utf-8", errors="ignore") if pine_path else None
            out["repaint"] = repaint.audit(cls, bars, sym, tf, src, params=params, full=res)
        out["seconds"] = time.perf_counter() - t0
        return out
    except Exception as e:                     # a broken conversion must not stop the run
        return {"ok": False, "path": path, "tickerid": ref_d["tickerid"], "tf": tf,
                "error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-2000:]}


def run_matrix(strategies: list[catalog.CatalogEntry] | None = None,
               symbols: list[data.SymbolRef] | None = None,
               timeframes: tuple[str, ...] = TIMEFRAMES, workers: int | None = None,
               n_bars: int = 20_000, db_url: str | None = None, refresh_data: bool = False,
               log=print) -> dict:
    strategies = strategies if strategies is not None else catalog.discover("strategies")
    symbols = symbols or data.DEFAULT_UNIVERSE
    workers = workers or max(1, (os.cpu_count() or 2) - 1)
    log(f"{len(strategies)} strategies × {len(symbols)} symbols × {len(timeframes)} timeframes, {workers} workers")

    # 1. data, sequentially
    available: list[tuple[data.SymbolRef, str]] = []
    for ref in symbols:
        for tf in timeframes:
            try:
                df = data.fetch(ref, tf, bars=n_bars, refresh=refresh_data)
                if len(df) >= 300:
                    available.append((ref, tf))
            except Exception as e:
                log(f"  data {ref.tickerid} {tf}: {type(e).__name__}: {str(e)[:120]}")
    log(f"data ready for {len(available)} symbol/timeframe pairs")

    # 2+3. jobs: the first available combination of each strategy also runs the audit
    jobs = []
    for e in strategies:
        first = True
        for ref, tf in available:
            jobs.append((str(e.path), asdict(ref), tf, None, n_bars, first,
                         str(e.pine_path) if e.pine_path else None))
            first = False
    results: list[dict] = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(job, j) for j in jobs]
        for k, f in enumerate(as_completed(futs), start=1):
            results.append(f.result())
            if k % 25 == 0 or k == len(futs):
                log(f"  {k}/{len(futs)} backtests  ({time.time() - t0:.0f}s)")
    failed = [r for r in results if not r["ok"]]
    for r in failed[:10]:
        log(f"  FAILED {Path(r['path']).name} {r['tickerid']} {r['tf']}: {r['error']}")

    # 4. score + store
    stored = store(strategies, [r for r in results if r["ok"]], db_url)
    return {"jobs": len(jobs), "ok": len(results) - len(failed), "failed": len(failed), **stored}


def store(strategies: list[catalog.CatalogEntry], results: list[dict], db_url: str | None = None) -> dict:
    eng = db.engine(db_url)
    by_path: dict[str, list[dict]] = {}
    for r in results:
        by_path.setdefault(r["path"], []).append(r)
    eligible = 0
    with Session(eng) as s:
        for e in strategies:
            rs = by_path.get(str(e.path), [])
            audit = next((r["repaint"] for r in rs if "repaint" in r), None)
            st = _upsert_strategy(s, e, audit, rs)
            repainting = bool(audit and audit["repainting"])
            profitable = [r for r in rs if (r["metrics"].get("netProfit") or 0) > 0]
            breadth = len(profitable) / len(rs) if len(rs) >= 3 else None
            for r in rs:
                sym = db.get_or_create_symbol(s, data.find_symbol(r["tickerid"]) or
                                              data.SymbolRef(r["tickerid"], "stock", "yahoo", r["tickerid"]))
                eligible += _upsert_backtest(s, st, sym, r, repainting, breadth)
        s.commit()
    return {"stored": len(results), "eligible": eligible}


def _upsert_strategy(s: Session, e: catalog.CatalogEntry, audit: dict | None, rs: list[dict]) -> db.Strategy:
    row = s.scalar(select(db.Strategy).where(db.Strategy.tv_id == e.tv_id))
    src = e.pine_path.read_text(encoding="utf-8", errors="ignore") if e.pine_path else ""
    info = catalog.analyse_pine(src, e.name) if src else {"indicators": [], "entryCriteria": [],
                                                           "exitCriteria": [], "tags": []}
    types = [r["strategy_type"] for r in rs if r.get("strategy_type")]
    main_type = max(set(types), key=types.count) if types else ""
    vals = dict(name=e.name, author=(e.script_cls.SOURCE or {}).get("author") or e.meta.get("author") or "",
                tradingview_url=(e.script_cls.SOURCE or {}).get("url") or e.meta.get("url") or "",
                module=str(e.path.relative_to(catalog.REPO)).replace("\\", "/"),
                pine_path=str(e.pine_path.relative_to(catalog.REPO)).replace("\\", "/") if e.pine_path else "",
                licence=(e.script_cls.SOURCE or {}).get("licence", ""), strategy_type=main_type,
                main_type=main_type, tags=info["tags"], indicators=info["indicators"],
                entry_criteria=info["entryCriteria"], exit_criteria=info["exitCriteria"],
                parameters=rs[0]["inputs"] if rs else [],
                repainting=db.clean(audit) if audit else {}, conversion_status=e.meta.get("python_status", ""),
                updated_at=datetime.now(timezone.utc))
    if row is None:
        row = db.Strategy(tv_id=e.tv_id, **vals)
        s.add(row)
    else:
        for k, v in vals.items():
            setattr(row, k, v)
    s.flush()
    return row


def _upsert_backtest(s: Session, st: db.Strategy, sym: db.Symbol, r: dict, repainting: bool,
                     breadth: float | None) -> int:
    m = db.clean(r["metrics"])
    trades = db.clean(r["trades"])
    eq = r["curves"]["equity"]
    score = scoring.robust_score(m, eq, trades, breadth)
    gate, reasons = scoring.quality_gate(m, repainting, r["bars"])
    fl = scoring.flags(m, trades)
    key = _params_key(r["params"])
    row = s.scalar(select(db.Backtest).where(db.Backtest.strategy_id == st.id, db.Backtest.symbol_id == sym.id,
                                             db.Backtest.timeframe == r["tf"], db.Backtest.params_key == key))
    full_metrics = {**m, **score, "qualityGatePass": gate,
                    "weightedScore": scoring.weighted_score(score["robustnessScore"], m)}
    vals = dict(params=r["params"], strategy_type=r["strategy_type"], bars=r["bars"],
                period_from=m.get("periodFrom"), period_to=m.get("periodTo"),
                latest_trade_time=m.get("latestTradeTime"),
                net_profit_percent=m.get("netProfitPercent"), profit_factor=_finite(m.get("profitFactor")),
                sharpe=m.get("sharpeRatio"), sortino=m.get("sortinoRatio"),
                max_drawdown_percent=m.get("maxDrawdownPercent"), total_trades=m.get("totalTrades"),
                percent_profitable=m.get("percentProfitable"), risk_reward=m.get("riskReward"),
                avg_trade_percent=m.get("avgTradePercent"), buy_hold_percent=m.get("buyHoldReturnPercent"),
                p_value=m.get("pValue"), robust_score=score["robustnessScore"],
                score_consistency=score["consistency"], score_backtests=score["backtests"],
                score_edge=score["edge"], score_practicality=score["practicality"],
                quality_gate_pass=gate, gate_reasons=reasons, flags=fl, metrics=db.clean(full_metrics),
                error="", updated_at=datetime.now(timezone.utc))
    if row is None:
        row = db.Backtest(strategy_id=st.id, symbol_id=sym.id, timeframe=r["tf"], params_key=key, **vals)
        s.add(row)
        s.flush()
        row.detail = db.BacktestDetail(backtest_id=row.id, trades=trades, equity_curve=db.clean(r["curves"]),
                                       monthly_returns=db.clean(r["monthly"]))
    else:
        for k, v in vals.items():
            setattr(row, k, v)
        if row.detail is None:
            row.detail = db.BacktestDetail(backtest_id=row.id)
        row.detail.trades = trades
        row.detail.equity_curve = db.clean(r["curves"])
        row.detail.monthly_returns = db.clean(r["monthly"])
    return 1 if gate else 0


def _finite(x):
    return 1e9 if x == math.inf else x


def _params_key(params: dict | None) -> str:
    if not params:
        return ""
    return "&".join(f"{k}={params[k]}" for k in sorted(params))[:250]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--timeframes", nargs="+", default=list(TIMEFRAMES))
    ap.add_argument("--symbols", nargs="*", help="tickerids or tickers; default: the built-in universe")
    ap.add_argument("--strategies", nargs="*", help="TradingView ids; default: all converted")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--bars", type=int, default=20_000)
    ap.add_argument("--refresh", action="store_true", help="refetch market data")
    a = ap.parse_args()
    ents = catalog.discover("strategies")
    if a.strategies:
        ents = [e for e in ents if e.tv_id in set(a.strategies)]
    syms = None
    if a.symbols:
        syms = [r for r in (data.find_symbol(q) for q in a.symbols) if r is not None]
    out = run_matrix(ents, syms, tuple(a.timeframes), a.workers, a.bars, refresh_data=a.refresh)
    print(out)


if __name__ == "__main__":
    main()
