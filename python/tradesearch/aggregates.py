"""
Aggregates TradeSearcher shows outside the search: platform counters, per-symbol
statistics, the 350-day leaderboard, and market listings.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import db
from .search import backtest_json, symbol_json


def _med(v: list[float]) -> float | None:
    v = [x for x in v if x is not None and x == x]
    return round(statistics.median(v), 4) if v else None


def _avg(v: list[float]) -> float | None:
    v = [x for x in v if x is not None and x == x and abs(x) < 1e8]
    return round(sum(v) / len(v), 4) if v else None


def platform_counters(s: Session) -> dict:
    total = s.scalar(select(func.count()).select_from(db.Backtest)) or 0
    eligible = s.scalar(select(func.count()).select_from(db.Backtest).where(db.Backtest.quality_gate_pass.is_(True))) or 0
    return {"analyzed": total, "eligible": eligible,
            "eligibleShare": round(eligible / total, 4) if total else None,
            "symbols": s.scalar(select(func.count(func.distinct(db.Backtest.symbol_id)))) or 0,
            "strategies": s.scalar(select(func.count(func.distinct(db.Backtest.strategy_id)))) or 0}


def symbol_stats(s: Session, sym: db.Symbol) -> dict:
    rows = s.scalars(select(db.Backtest).where(db.Backtest.symbol_id == sym.id)).all()
    if not rows:
        return {"symbol": symbol_json(sym), "backtestsRun": 0}
    beat = [b for b in rows if b.net_profit_percent is not None and b.buy_hold_percent is not None
            and b.net_profit_percent > b.buy_hold_percent]
    by_type: dict[str, list[db.Backtest]] = defaultdict(list)
    for b in rows:
        by_type[b.strategy_type or "unknown"].append(b)
    by_tf: dict[str, list[db.Backtest]] = defaultdict(list)
    for b in rows:
        if b.quality_gate_pass:          # sub-viable runs (e.g. 1 share on $1M) make Sharpe explode
            by_tf[b.timeframe].append(b)
    tf_sharpe = {tf: _avg([b.sharpe for b in bs]) for tf, bs in by_tf.items()}
    best_tf = max((tf for tf in tf_sharpe if tf_sharpe[tf] is not None), key=lambda t: tf_sharpe[t], default=None)
    top = sorted([b for b in rows if b.quality_gate_pass and b.profit_factor is not None],
                 key=lambda b: -b.profit_factor)[:10]
    periods = [b.period_from for b in rows if b.period_from] + [b.period_to for b in rows if b.period_to]
    return {
        "symbol": symbol_json(sym, s),
        "backtestsRun": len(rows),
        "strategiesListed": len({b.strategy_id for b in rows}),
        "beatBuyHoldPercent": round(100 * len(beat) / len(rows), 2),
        "medianNetProfitPercent": _med([b.net_profit_percent for b in rows]),
        "averageWinRate": _avg([b.percent_profitable for b in rows]),
        "medianMaxDrawdownPercent": _med([b.max_drawdown_percent for b in rows]),
        "priceDataFrom": min(periods) if periods else None, "priceDataTo": max(periods) if periods else None,
        "byStrategyType": [{"type": t, "backtests": len(bs),
                            "medianNetProfitPercent": _med([b.net_profit_percent for b in bs]),
                            "averageWinRate": _avg([b.percent_profitable for b in bs]),
                            "medianMaxDrawdownPercent": _med([b.max_drawdown_percent for b in bs]),
                            "averageSharpe": _avg([b.sharpe for b in bs])} for t, bs in sorted(by_type.items())],
        "bestTimeframe": {"timeframe": best_tf, "averageSharpe": tf_sharpe.get(best_tf),
                          "backtests": len(by_tf.get(best_tf, []))} if best_tf else None,
        "topByProfitFactor": [{"backtestId": b.id, "strategy": b.strategy.name, "timeframe": b.timeframe,
                               "profitFactor": b.profit_factor, "winRate": b.percent_profitable,
                               "netProfitPercent": b.net_profit_percent, "trades": b.total_trades} for b in top],
    }


def markets(s: Session) -> dict:
    out: dict[str, list] = defaultdict(list)
    for sym in s.scalars(select(db.Symbol)).all():
        n = s.scalar(select(func.count(func.distinct(db.Backtest.strategy_id))).where(
            db.Backtest.symbol_id == sym.id, db.Backtest.quality_gate_pass.is_(True))) or 0
        out[sym.type].append({**symbol_json(sym), "strategies": n})
    for k in out:
        out[k].sort(key=lambda d: -d["strategies"])
    return dict(out)


def leaderboard(s: Session, days: int = 350, limit: int = 20, benchmark: str = "BINANCE:BTCUSDT") -> dict:
    """Eligible backtests' equity over the last ``days``, rebased to 100 at the window start,
    ranked by return over the window; with the benchmark's buy & hold over the same window."""
    rows = s.scalars(select(db.Backtest).where(db.Backtest.quality_gate_pass.is_(True))).all()
    entries = []
    for b in rows:
        if b.detail is None or not b.period_to:
            continue
        c = b.detail.equity_curve or {}
        t, eq = c.get("time", []), c.get("equity", [])
        start = b.period_to - days * 86_400_000
        idx = [k for k, x in enumerate(t) if x >= start]
        if len(idx) < 2 or not eq[idx[0]]:
            continue
        base = eq[idx[0]]
        curve = [{"time": t[k], "value": 100.0 * eq[k] / base} for k in idx]
        entries.append({"return": curve[-1]["value"] - 100.0, "curve": curve, "backtest": backtest_json(b)})
    entries.sort(key=lambda e: -e["return"])
    bench = None
    sym = s.scalar(select(db.Symbol).where(db.Symbol.tickerid == benchmark))
    if sym is not None:
        bb = s.scalars(select(db.Backtest).where(db.Backtest.symbol_id == sym.id)).first()
        if bb is not None and bb.detail is not None:
            c = bb.detail.equity_curve or {}
            t, bh = c.get("time", []), c.get("buyHold", [])
            start = (bb.period_to or 0) - days * 86_400_000
            idx = [k for k, x in enumerate(t) if x >= start]
            if len(idx) >= 2 and bh[idx[0]]:
                bench = {"symbol": benchmark,
                         "curve": [{"time": t[k], "value": 100.0 * bh[k] / bh[idx[0]]} for k in idx]}
    return {"days": days, "data": entries[:limit], "benchmark": bench,
            "note": "Past performance is not indicative of future results."}
