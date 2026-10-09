"""
MCP server (stdio, JSON-RPC 2.0) with TradeSearcher's seven agent tools — same names and
parameters — answered from the local database. Register it with Claude Code:

    claude mcp add tradesearch -- python -m tradesearch.mcp_server     (run from python/)
"""

from __future__ import annotations

import json
import sys

from sqlalchemy.orm import Session

from . import db, search

TOOLS = [
    {"name": "search_symbols", "description": "Map short inputs like AAPL to full symbols like NASDAQ:AAPL.",
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "number"}},
                     "required": ["query"]}},
    {"name": "search_backtests", "description": "Search backtests by market, timeframe and minimum metrics.",
     "inputSchema": {"type": "object", "properties": {
         "symbol": {"type": "string"}, "market": {"type": "string", "enum": ["crypto", "stock", "forex", "futures"]},
         "timeframe": {"type": "string"}, "strategyType": {"type": "string", "enum": ["intraday", "swing", "longTerm"]},
         "minSharpe": {"type": "number"}, "minProfitFactor": {"type": "number"}, "maxDrawdown": {"type": "number"},
         "sort": {"type": "string", "enum": list(search.SORTS)}, "order": {"type": "string", "enum": ["desc", "asc"]},
         "limit": {"type": "number"}}}},
    {"name": "get_best_for_symbol", "description": "Get the top ranked backtests for a symbol.",
     "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string"}, "limit": {"type": "number"}},
                     "required": ["symbol"]}},
    {"name": "get_backtest", "description": "Fetch one backtest, optionally with trades and equity curve.",
     "inputSchema": {"type": "object", "properties": {"id": {"type": "number"}, "includeTrades": {"type": "boolean"},
                                                      "tradeLimit": {"type": "number"},
                                                      "includeEquityCurve": {"type": "boolean"}},
                     "required": ["id"]}},
    {"name": "get_strategy", "description": "Get strategy metadata and optional Pine source code.",
     "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}, "includeSourceCode": {"type": "boolean"}},
                     "required": ["id"]}},
    {"name": "compare_backtests", "description": "Compare selected backtests in compact form.",
     "inputSchema": {"type": "object", "properties": {"ids": {"type": "array", "items": {"type": "number"}}},
                     "required": ["ids"]}},
    {"name": "get_account_status", "description": "Show the current account tier and limits.",
     "inputSchema": {"type": "object", "properties": {}}},
]


def call(s: Session, name: str, a: dict) -> dict:
    if name == "search_symbols":
        return search.search_symbols(s, a.get("query", ""), int(a.get("limit", 10)))
    if name == "search_backtests":
        keep = {k: a[k] for k in ("symbol", "market", "timeframe", "strategyType", "minSharpe", "minProfitFactor",
                                   "maxDrawdown", "sort", "order") if k in a}
        return search.search_backtests(s, limit=int(a.get("limit", 20)), **keep)
    if name == "get_best_for_symbol":
        return search.best_for_symbol(s, a["symbol"], int(a.get("limit", 10)))
    if name == "get_backtest":
        return search.get_backtest(s, int(a["id"]), bool(a.get("includeTrades")), int(a.get("tradeLimit", 20)),
                                   bool(a.get("includeEquityCurve")))
    if name == "get_strategy":
        return search.get_strategy(s, a["id"], bool(a.get("includeSourceCode")))
    if name == "compare_backtests":
        return search.compare_backtests(s, [int(x) for x in a.get("ids", [])])
    if name == "get_account_status":
        return {"data": {"tier": "self-hosted", "limitSummary": "no limits"}}
    raise ValueError(f"unknown tool {name}")


def main() -> None:
    eng = db.engine()
    for line in sys.stdin:
        if not line.strip():
            continue
        msg = json.loads(line)
        mid, method = msg.get("id"), msg.get("method")
        try:
            if method == "initialize":
                result = {"protocolVersion": msg.get("params", {}).get("protocolVersion", "2025-06-18"),
                          "capabilities": {"tools": {}}, "serverInfo": {"name": "tradesearch", "version": "0.1.0"}}
            elif method == "tools/list":
                result = {"tools": TOOLS}
            elif method == "tools/call":
                p = msg["params"]
                with Session(eng) as s:
                    out = call(s, p["name"], p.get("arguments") or {})
                result = {"content": [{"type": "text", "text": json.dumps(db.clean(out), ensure_ascii=False)}]}
            elif method and method.startswith("notifications/"):
                continue
            else:
                raise ValueError(f"method not supported: {method}")
            resp = {"jsonrpc": "2.0", "id": mid, "result": result}
        except Exception as e:
            resp = {"jsonrpc": "2.0", "id": mid, "error": {"code": -32000, "message": str(e)}}
        if mid is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
