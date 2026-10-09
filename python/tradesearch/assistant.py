"""
"Find my strategy": a short questionnaire turned into search filters and a ranked shortlist,
with the reason each strategy fits.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from . import search

QUESTIONS = [
    {"id": "market", "question": "Which market do you trade?", "options": ["crypto", "stock", "forex", "futures", "any"]},
    {"id": "style", "question": "How long do you hold a trade?",
     "options": ["intraday", "swing", "longTerm", "any"]},
    {"id": "risk", "question": "What drawdown can you live with?", "options": ["low", "medium", "high"]},
    {"id": "frequency", "question": "How often do you want signals?", "options": ["rarely", "weekly", "daily", "many"]},
    {"id": "winrate", "question": "Do you need to win most trades to stay disciplined?", "options": ["yes", "no"]},
    {"id": "symbol", "question": "A specific symbol? (optional)", "options": []},
]

_RISK_DD = {"low": 15.0, "medium": 30.0, "high": 60.0}
_FREQ_TF = {"rarely": ["D"], "weekly": ["240", "D"], "daily": ["60", "240"], "many": ["15", "60"]}


def recommend(s: Session, answers: dict[str, Any], limit: int = 10) -> dict:
    market = answers.get("market")
    style = answers.get("style")
    filters = {
        "market": None if market in (None, "", "any") else market,
        "strategyType": None if style in (None, "", "any") else style,
        "maxDrawdown": _RISK_DD.get(answers.get("risk", "medium"), 30.0),
        "minWinRate": 50.0 if answers.get("winrate") == "yes" else None,
        "minTrades": 30,
        "symbol": answers.get("symbol") or None,
    }
    tfs = _FREQ_TF.get(answers.get("frequency", ""), [None])
    rows: list[dict] = []
    for tf in tfs:
        res = search.search_backtests(s, timeframe=tf, sort="robustness", limit=limit * 2,
                                      **{k: v for k, v in filters.items() if v is not None})
        rows.extend(res["data"])
    rows.sort(key=lambda d: -(d["metrics"].get("robustnessScore") or 0))
    seen, picks = set(), []
    for d in rows:
        k = (d["strategy"]["id"], d["symbol"]["name"])
        if k in seen:
            continue
        seen.add(k)
        d["why"] = _why(d, answers, filters)
        picks.append(d)
        if len(picks) >= limit:
            break
    return {"data": picks, "meta": {"filters": filters, "timeframes": tfs, "questions": QUESTIONS}}


def _why(d: dict, answers: dict, f: dict) -> list[str]:
    m = d["metrics"]
    out = [f"Robust Score {m.get('robustnessScore')}/100"]
    if f.get("maxDrawdown") is not None and m.get("maxDrawdownPercent") is not None:
        out.append(f"max drawdown {m['maxDrawdownPercent']:.1f}% (your limit {f['maxDrawdown']:.0f}%)")
    if m.get("percentProfitable") is not None:
        out.append(f"wins {m['percentProfitable']:.0f}% of trades")
    if d.get("strategyType"):
        out.append(f"{d['strategyType']} holding period on the {d['timeframe']} timeframe")
    return out
