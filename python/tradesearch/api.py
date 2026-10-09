"""
HTTP API (FastAPI). Run:  uvicorn tradesearch.api:app --reload   (from python/)

/api/agent/*  — TradeSearcher's agent API: same paths, parameters and response shapes
                ({data, meta, account, limits}) as its CLI/MCP client expects
/api/*        — what the web app needs: counters, markets, symbol pages, leaderboard,
                strategy library, assistant, calculators, on-demand backtests
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import Body, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from . import aggregates, assistant, calculators, catalog, data, db, search

ACCOUNT = {"tier": "self-hosted", "limitSummary": "no limits", "upgradeUrl": None}
LIMITS = {"isLimited": False}


class CleanJSON(JSONResponse):
    """JSON without NaN/Infinity (they become null) — Starlette rejects them otherwise."""

    def render(self, content: Any) -> bytes:
        return json.dumps(db.clean(content), ensure_ascii=False, separators=(",", ":")).encode("utf-8")


app = FastAPI(title="TradeSearch", version="0.1.0", default_response_class=CleanJSON)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
_ENGINE = None


def session():
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = db.engine()
    with Session(_ENGINE) as s:
        yield s


def _wrap(payload: dict) -> dict:
    payload.setdefault("account", ACCOUNT)
    payload.setdefault("limits", LIMITS)
    if payload.get("data") is None and payload.get("error"):
        raise HTTPException(404, payload["error"]["message"])
    return payload


# ─────────────────────────────────────────────────────────────── agent API
@app.get("/api/agent/account")
def agent_account():
    return {"data": ACCOUNT, "account": ACCOUNT, "limits": LIMITS}


@app.get("/api/agent/symbols")
def agent_symbols(query: str = "", limit: int = 10, s: Session = Depends(session)):
    return _wrap(search.search_symbols(s, query, limit))


@app.get("/api/agent/search-backtests")
def agent_search(symbol: str | None = None, market: str | None = None, timeframe: str | None = None,
                 strategyType: str | None = None, minSharpe: float | None = None,
                 minProfitFactor: float | None = None, maxDrawdown: float | None = None,
                 minWinRate: float | None = None, minTrades: int | None = None,
                 minRobustness: float | None = None, strategy: str | None = None, period: str | None = None,
                 eligibleOnly: bool = True, sort: str = "robustness", order: str = "desc",
                 limit: int = Query(20, le=500), offset: int = 0, s: Session = Depends(session)):
    return _wrap(search.search_backtests(
        s, symbol=symbol, market=market, timeframe=timeframe, strategyType=strategyType, minSharpe=minSharpe,
        minProfitFactor=minProfitFactor, maxDrawdown=maxDrawdown, minWinRate=minWinRate, minTrades=minTrades,
        minRobustness=minRobustness, strategy=strategy, period=period, eligibleOnly=eligibleOnly,
        sort=sort, order=order, limit=limit, offset=offset))


@app.get("/api/agent/best-for-symbol")
def agent_best(symbol: str, limit: int = 10, s: Session = Depends(session)):
    return _wrap(search.best_for_symbol(s, symbol, limit))


@app.get("/api/agent/backtests/{id}")
def agent_backtest(id: int, includeTrades: bool = False, tradeLimit: int = 20, includeEquityCurve: bool = False,
                   s: Session = Depends(session)):
    return _wrap(search.get_backtest(s, id, includeTrades, tradeLimit, includeEquityCurve))


@app.get("/api/agent/strategies/{id}")
def agent_strategy(id: str, includeSourceCode: bool = False, s: Session = Depends(session)):
    return _wrap(search.get_strategy(s, id, includeSourceCode))


@app.get("/api/agent/compare")
def agent_compare(ids: str, s: Session = Depends(session)):
    return _wrap(search.compare_backtests(s, [int(x) for x in ids.split(",") if x.strip().isdigit()]))


# ─────────────────────────────────────────────────────────────── app API
@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/stats/platform")
def stats_platform(s: Session = Depends(session)):
    return aggregates.platform_counters(s)


@app.get("/api/markets")
def markets(s: Session = Depends(session)):
    return aggregates.markets(s)


@app.get("/api/symbols/{symbol}/stats")
def symbol_stats(symbol: str, s: Session = Depends(session)):
    sym = search.resolve_symbol(s, symbol)
    if sym is None:
        raise HTTPException(404, f"symbol {symbol} not found")
    return aggregates.symbol_stats(s, sym)


@app.get("/api/leaderboard")
def leaderboard(days: int = 350, limit: int = 20, benchmark: str = "BINANCE:BTCUSDT", s: Session = Depends(session)):
    return aggregates.leaderboard(s, days, limit, benchmark)


@app.get("/api/strategies")
def strategies(q: str | None = None, tag: str | None = None, strategyType: str | None = None,
               indicator: str | None = None, limit: int = 50, offset: int = 0, s: Session = Depends(session)):
    rows = s.scalars(select(db.Strategy).order_by(db.Strategy.name)).all()
    out = []
    for st in rows:
        if q and q.lower() not in st.name.lower():
            continue
        if tag and tag not in (st.tags or []):
            continue
        if strategyType and st.strategy_type != strategyType:
            continue
        if indicator and indicator not in (st.indicators or []):
            continue
        bts = s.scalars(select(db.Backtest).where(db.Backtest.strategy_id == st.id)).all()
        out.append({**search.strategy_summary(st), "tvId": st.tv_id, "author": st.author, "tags": st.tags,
                    "indicators": st.indicators, "averages": search.averages(bts),
                    "repainting": {k: v for k, v in (st.repainting or {}).items() if k != "tests"}})
    return {"data": out[offset:offset + limit], "meta": {"total": len(out)}}


@app.get("/api/strategies/{id}/backtests")
def strategy_backtests(id: str, eligibleOnly: bool = False, limit: int = 100, s: Session = Depends(session)):
    res = search.get_strategy(s, id)
    if res.get("data") is None:
        raise HTTPException(404, "strategy not found")
    return search.search_backtests(s, strategy=res["data"]["tvId"], eligibleOnly=eligibleOnly, limit=limit)


@app.get("/api/assistant/questions")
def assistant_questions():
    return {"data": assistant.QUESTIONS}


@app.post("/api/assistant")
def assistant_recommend(answers: dict = Body(...), limit: int = 10, s: Session = Depends(session)):
    return assistant.recommend(s, answers, limit)


@app.get("/api/tools")
def tools():
    return {"data": [{"id": k, "doc": (f.__doc__ or "").strip()} for k, f in calculators.CALCULATORS.items()]}


@app.post("/api/tools/{name}")
def tool(name: str, params: dict = Body(...)):
    fn = calculators.CALCULATORS.get(name)
    if fn is None:
        raise HTTPException(404, f"unknown calculator {name}")
    try:
        return {"data": fn(**params)}
    except TypeError as e:
        raise HTTPException(422, str(e))


@app.post("/api/backtests/run")
def run_backtest(body: dict = Body(...)):
    """On-demand backtest (e.g. with different parameters): {strategy, symbol, timeframe,
    params?, bars?, strategyOverrides?}. Not stored."""
    from pinelib import metrics, run
    from .pipeline import _symbolinfo
    from dataclasses import asdict
    tv_id = str(body.get("strategy", ""))
    entry = next((e for e in catalog.discover("strategies") if e.tv_id == tv_id), None)
    if entry is None:
        raise HTTPException(404, f"strategy {tv_id} is not converted")
    ref = data.find_symbol(str(body.get("symbol", "")))
    if ref is None:
        raise HTTPException(404, "unknown symbol")
    tf = str(body.get("timeframe", "60"))
    bars = data.fetch(ref, tf, bars=int(body.get("bars", 20_000)))
    res = run(entry.script_cls, bars, params=body.get("params"), symbol=_symbolinfo(asdict(ref)), timeframe=tf,
              strategy_overrides=body.get("strategyOverrides"))
    return {"data": {"metrics": metrics.compute(res), "trades": metrics.trades_table(res)[-200:],
                     "curves": metrics.curves(res, points=1000), "inputs": res.inputs}}
