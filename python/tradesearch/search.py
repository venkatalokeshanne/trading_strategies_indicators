"""
Search and ranking — the same parameters and response shapes as TradeSearcher's agent API
(search_symbols, search_backtests, get_best_for_symbol, get_backtest, get_strategy,
compare_backtests), plus the app's extra filters (win rate, trade count, period windows).
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from . import catalog, db, scoring

SORTS = {
    "sharpe": db.Backtest.sharpe, "sharpeRatio": db.Backtest.sharpe,
    "profitFactor": db.Backtest.profit_factor, "roi": db.Backtest.net_profit_percent,
    "netProfitPercent": db.Backtest.net_profit_percent, "latestTradeDate": db.Backtest.latest_trade_time,
    "robustness": db.Backtest.robust_score, "riskReward": db.Backtest.risk_reward,
    "winRate": db.Backtest.percent_profitable, "trades": db.Backtest.total_trades,
    "maxDrawdown": db.Backtest.max_drawdown_percent,
}
WINDOWS = {"3m": 91, "6m": 182, "1y": 365, "350d": 350, "2y": 730}


def _iso(ms: int | None) -> str | None:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat() if ms else None


# ─────────────────────────────────────────────────────────────── serialisation
def symbol_json(sym: db.Symbol, s: Session | None = None, **extra: Any) -> dict:
    out = {"id": sym.id, "name": sym.tickerid, "ticker": sym.ticker, "type": sym.type,
           "exchange": sym.exchange, "description": sym.description, "currency": sym.currency,
           "baseCurrency": sym.base_currency}
    if s is not None:
        out["backtestsCount"] = s.scalar(select(func.count()).select_from(db.Backtest)
                                         .where(db.Backtest.symbol_id == sym.id)) or 0
    out.update(extra)
    return out


def strategy_summary(st: db.Strategy) -> dict:
    avail = "available" if st.pine_path else "no"
    return {"id": st.id, "name": st.name, "strategyType": st.strategy_type, "mainType": st.main_type,
            "sourceAvailability": avail, "sourceAvailable": avail == "available"}


def backtest_json(b: db.Backtest, *, details: bool = False, trades: bool = False, trade_limit: int = 20,
                  equity: bool = False) -> dict:
    m = dict(b.metrics or {})
    out = {
        "id": b.id, "symbol": symbol_json(b.symbol), "strategy": strategy_summary(b.strategy),
        "timeframe": b.timeframe, "strategyType": b.strategy_type,
        "latestTradeDate": _iso(b.latest_trade_time),
        "period": {"from": _iso(b.period_from), "to": _iso(b.period_to)},
        "parameters": b.params or {},
        "metrics": m if details else _compact_metrics(m),
        "qualityGate": {"pass": b.quality_gate_pass, "reasons": b.gate_reasons or []},
        "flags": b.flags or [],
        "updatedAt": b.updated_at.isoformat() if b.updated_at else None,
    }
    if (trades or equity) and b.detail is not None:
        if trades:
            rows = list(reversed(b.detail.trades or []))
            out["trades"] = rows[:trade_limit]
            out["tradeResultInfo"] = {"tradesReturned": len(out["trades"]), "tradesTotalBeforeLimit": len(rows),
                                      "appliedTradeLimit": trade_limit}
        if equity:
            c = b.detail.equity_curve or {}
            t = c.get("time", [])
            out["equityCurve"] = [{"time": x, "value": v} for x, v in zip(t, c.get("equity", []))]
            out["drawdownCurve"] = [{"time": x, "value": v} for x, v in zip(t, c.get("drawdownPercent", []))]
            out["buyHoldCurve"] = [{"time": x, "value": v} for x, v in zip(t, c.get("buyHold", []))]
            out["monthlyReturns"] = b.detail.monthly_returns or []
    return out


def _compact_metrics(m: dict) -> dict:
    keys = ("netProfitPercent", "profitFactor", "sharpeRatio", "sortinoRatio", "maxDrawdownPercent",
            "totalTrades", "percentProfitable", "riskReward", "avgTradePercent", "buyHoldReturnPercent",
            "robustnessScore", "consistency", "backtests", "edge", "practicality", "qualityGatePass",
            "pValue", "tStat")
    return {k: m.get(k) for k in keys}


def strategy_json(s: Session, st: db.Strategy, include_source: bool = False) -> dict:
    rows = s.scalars(select(db.Backtest).where(db.Backtest.strategy_id == st.id)).all()
    out = {**strategy_summary(st), "tvId": st.tv_id, "author": st.author, "tradingViewUrl": st.tradingview_url,
           "description": st.description, "summary": st.summary or _summary(st), "tags": st.tags,
           "tagCategories": {"style": [t for t in st.tags if t in ("Scalping", "Swing", "Trend following",
                                                                    "Mean reversion", "Breakout", "Momentum")],
                             "market": [t for t in st.tags if t in ("Crypto", "Forex & gold", "Futures")]},
           "timeframes": sorted({b.timeframe for b in rows}, key=_tf_order),
           "tradeability": _tradeability(rows), "indicators": st.indicators,
           "entryCriteria": st.entry_criteria, "exitCriteria": st.exit_criteria,
           "parameters": st.parameters, "repainting": st.repainting, "averages": averages(rows),
           "licence": st.licence, "pythonModule": st.module, "pinePath": st.pine_path}
    if include_source and st.pine_path:
        p = catalog.REPO / st.pine_path
        if p.exists():
            out["sourceCode"] = p.read_text(encoding="utf-8", errors="ignore")
    return out


def _summary(st: db.Strategy) -> str:
    ind = ", ".join(st.indicators[:4]) or "custom logic"
    ent = ", ".join(c.lower() for c in st.entry_criteria[:2])
    ex = ", ".join(c.lower() for c in st.exit_criteria[:2])
    return f"Uses {ind}. Enters on {ent}; exits on {ex}."


def _tf_order(tf: str) -> int:
    from pinelib import tf_seconds
    try:
        return tf_seconds(tf)
    except Exception:
        return 10 ** 9


def _tradeability(rows: list[db.Backtest]) -> dict:
    elig = [b for b in rows if b.quality_gate_pass]
    return {"eligibleBacktests": len(elig), "totalBacktests": len(rows),
            "eligibleShare": round(len(elig) / len(rows), 3) if rows else None}


def averages(rows: list[db.Backtest]) -> dict:
    def avg(attr):
        v = [getattr(b, attr) for b in rows if getattr(b, attr) is not None and getattr(b, attr) == getattr(b, attr)]
        v = [x for x in v if abs(x) < 1e8]
        return round(sum(v) / len(v), 4) if v else None
    return {"tests": len(rows), "netProfitPercent": avg("net_profit_percent"), "profitFactor": avg("profit_factor"),
            "sharpeRatio": avg("sharpe"), "maxDrawdownPercent": avg("max_drawdown_percent"),
            "percentProfitable": avg("percent_profitable"), "robustnessScore": avg("robust_score")}


# ─────────────────────────────────────────────────────────────── symbols
def search_symbols(s: Session, query: str, limit: int = 10) -> dict:
    q = (query or "").strip()
    ql = q.lower().replace("/", "")
    rows = s.scalars(select(db.Symbol)).all()
    scored = []
    for r in rows:
        name, tick, desc = r.tickerid.lower(), r.ticker.lower(), (r.description or "").lower()
        if ql == name or ql == tick:
            score, reason = 100, "exact ticker"
        elif tick.startswith(ql) or name.endswith(":" + ql):
            score, reason = 80, "ticker prefix"
        elif ql in tick or ql in name:
            score, reason = 60, "ticker contains query"
        elif ql and ql in desc:
            score, reason = 50, "description"
        else:
            continue
        scored.append((score, r, reason))
    scored.sort(key=lambda x: (-x[0], x[1].tickerid))
    data = [symbol_json(r, s, matchReason=reason) for _, r, reason in scored[:limit]]
    if data:
        best = max(data, key=lambda d: d.get("backtestsCount", 0))
        best["recommended"] = True
        best["recommendationReason"] = "most backtests among the matches"
    return {"data": data, "meta": {"query": query, "total": len(scored)}}


def resolve_symbol(s: Session, q: str) -> db.Symbol | None:
    if not q:
        return None
    hit = search_symbols(s, q, 1)["data"]
    return s.get(db.Symbol, hit[0]["id"]) if hit else None


# ─────────────────────────────────────────────────────────────── backtests
def search_backtests(s: Session, *, symbol: str | None = None, market: str | None = None,
                     timeframe: str | None = None, strategyType: str | None = None,
                     minSharpe: float | None = None, minProfitFactor: float | None = None,
                     maxDrawdown: float | None = None, minWinRate: float | None = None,
                     minTrades: int | None = None, minRobustness: float | None = None,
                     strategy: str | None = None, period: str | None = None,
                     eligibleOnly: bool = True, sort: str = "robustness", order: str = "desc",
                     limit: int = 20, offset: int = 0) -> dict:
    q = select(db.Backtest).join(db.Symbol).join(db.Strategy)
    meta: dict[str, Any] = {"filters": {}}
    if eligibleOnly:
        q = q.where(db.Backtest.quality_gate_pass.is_(True))
    if symbol:
        sym = resolve_symbol(s, symbol)
        meta["symbolMatch"] = {"query": symbol, "matched": symbol_json(sym) if sym else None}
        if sym is None:
            return {"data": [], "meta": meta}
        q = q.where(db.Backtest.symbol_id == sym.id)
    if market:
        q = q.where(db.Symbol.type == market)
    if timeframe:
        q = q.where(db.Backtest.timeframe == str(timeframe))
    if strategyType:
        q = q.where(db.Backtest.strategy_type == strategyType)
    if strategy:
        q = q.where(or_(db.Strategy.tv_id == strategy, db.Strategy.name.ilike(f"%{strategy}%")))
    for col, val, op in ((db.Backtest.sharpe, minSharpe, "ge"), (db.Backtest.profit_factor, minProfitFactor, "ge"),
                         (db.Backtest.max_drawdown_percent, maxDrawdown, "le"),
                         (db.Backtest.percent_profitable, minWinRate, "ge"),
                         (db.Backtest.total_trades, minTrades, "ge"),
                         (db.Backtest.robust_score, minRobustness, "ge")):
        if val is not None:
            q = q.where(col >= val if op == "ge" else col <= val)
    if period and period in WINDOWS:
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        q = q.where(db.Backtest.latest_trade_time >= now_ms - WINDOWS[period] * 86_400_000)
    col = SORTS.get(sort, db.Backtest.robust_score)
    q = q.order_by(col.asc().nulls_last() if order == "asc" else col.desc().nulls_last(), db.Backtest.id)
    total = s.scalar(select(func.count()).select_from(q.subquery()))
    rows = s.scalars(q.offset(offset).limit(limit)).all()
    data = [backtest_json(b) for b in rows]
    if period and period in WINDOWS:
        for d, b in zip(data, rows):
            d["windowMetrics"] = window_metrics(b, WINDOWS[period])
    meta.update({"total": total, "sort": sort, "order": order, "limit": limit, "offset": offset})
    return {"data": data, "meta": meta}


def window_metrics(b: db.Backtest, days: int) -> dict:
    """Trade-based metrics over the last ``days`` of the backtest (TradeSearcher's
    'last 3 / 6 months' views)."""
    trades = (b.detail.trades if b.detail else []) or []
    end = b.period_to or 0
    since = end - days * 86_400_000
    sel = [t for t in trades if t["exit"]["time"] >= since]
    init = (b.metrics or {}).get("initialCapital") or 1.0
    wins = [t["profit"] for t in sel if t["profit"] > 0]
    losses = [-t["profit"] for t in sel if t["profit"] < 0]
    gp, gl = sum(wins), sum(losses)
    aw = gp / len(wins) if wins else None
    al = gl / len(losses) if losses else None
    return {"days": days, "trades": len(sel), "netProfitPercent": 100 * sum(t["profit"] for t in sel) / init,
            "profitFactor": (gp / gl) if gl else None, "percentProfitable": 100 * len(wins) / len(sel) if sel else None,
            "riskReward": (aw / al) if (aw and al) else None}


def best_for_symbol(s: Session, symbol: str, limit: int = 10) -> dict:
    sym = resolve_symbol(s, symbol)
    if sym is None:
        return {"data": [], "meta": {"symbolMatch": {"query": symbol, "matched": None},
                                     "symbolSuggestions": search_symbols(s, symbol[:3], 5)["data"]}}
    rows = s.scalars(select(db.Backtest).where(db.Backtest.symbol_id == sym.id,
                                               db.Backtest.quality_gate_pass.is_(True))).all()
    ranked = sorted(rows, key=lambda b: -(b.metrics or {}).get("weightedScore", b.robust_score or 0))
    data = [{"rank": k, "weightedScore": (b.metrics or {}).get("weightedScore"),
             "latestTradeDate": _iso(b.latest_trade_time), "backtest": backtest_json(b)}
            for k, b in enumerate(ranked[:limit], start=1)]
    return {"data": data, "meta": {
        "symbolMatch": {"query": symbol, "matched": symbol_json(sym, s)},
        "ranking": "eligible backtests only (quality gate + no repainting), ordered by weightedScore = "
                   "Robust Score × (0.85 + 0.15 × recency of the latest trade)"}}


def get_backtest(s: Session, id: int, includeTrades: bool = False, tradeLimit: int = 20,
                 includeEquityCurve: bool = False) -> dict:
    b = s.get(db.Backtest, int(id))
    if b is None:
        return {"data": None, "error": {"message": f"backtest {id} not found"}}
    return {"data": backtest_json(b, details=True, trades=includeTrades, trade_limit=tradeLimit,
                                  equity=includeEquityCurve)}


def get_strategy(s: Session, id: int | str, includeSourceCode: bool = False) -> dict:
    st = s.get(db.Strategy, int(id)) if str(id).isdigit() else \
        s.scalar(select(db.Strategy).where(db.Strategy.tv_id == str(id)))
    if st is None:
        return {"data": None, "error": {"message": f"strategy {id} not found"}}
    return {"data": strategy_json(s, st, includeSourceCode)}


def compare_backtests(s: Session, ids: list[int]) -> dict:
    out = []
    for i in ids:
        b = s.get(db.Backtest, int(i))
        if b is None:
            continue
        m = b.metrics or {}
        out.append({"id": b.id, "symbol": b.symbol.tickerid, "strategy": b.strategy.name, "timeframe": b.timeframe,
                    "strategyType": b.strategy_type, "netProfitPercent": m.get("netProfitPercent"),
                    "profitFactor": m.get("profitFactor"), "sharpeRatio": m.get("sharpeRatio"),
                    "sortinoRatio": m.get("sortinoRatio"), "maxDrawdownPercent": m.get("maxDrawdownPercent"),
                    "totalTrades": m.get("totalTrades"), "percentProfitable": m.get("percentProfitable"),
                    "riskReward": m.get("riskReward"), "robustnessScore": m.get("robustnessScore"),
                    "latestTradeDate": _iso(b.latest_trade_time),
                    "sourceAvailability": strategy_summary(b.strategy)["sourceAvailability"]})
    return {"data": out}
