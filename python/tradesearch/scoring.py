"""
Quality gate and Robust Score.

TradeSearcher publishes the SHAPE of its score — 0–100, from Consistency, Backtests
(breadth of evidence), Edge (statistical edge) and Practicality — but not its formula.
This is a documented design with the same four components; every threshold is a named
constant so the ranking can be tuned in one place.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

# ─────────────────────────────────────────────────────────────── quality gate
GATE = {
    "min_trades": 20,
    "min_bars": 500,
    "max_drawdown_percent": 80.0,
    "min_profit_factor": 1.0,
    "min_net_profit_percent": 1.0,    # sub-viable: 1 share on $1M "profits" 0.0 %
    "recent_trade_days": 180,         # or a trade in the last quarter of the period
}


def quality_gate(m: dict, repainting: bool, bars: int) -> tuple[bool, list[str]]:
    """Viability: is this backtest worth ranking at all?"""
    reasons = []
    if repainting:
        reasons.append("repainting: failed the replay or look-ahead checks")
    if (m.get("totalTrades") or 0) < GATE["min_trades"]:
        reasons.append(f"fewer than {GATE['min_trades']} closed trades")
    if bars < GATE["min_bars"]:
        reasons.append(f"fewer than {GATE['min_bars']} bars of history")
    if not _gt(m.get("netProfitPercent"), GATE["min_net_profit_percent"]):
        reasons.append(f"net profit below {GATE['min_net_profit_percent']} % of capital")
    if not _gt(m.get("profitFactor"), GATE["min_profit_factor"]):
        reasons.append(f"profit factor ≤ {GATE['min_profit_factor']}")
    dd = m.get("maxDrawdownPercent")
    if dd is None or dd != dd or dd >= GATE["max_drawdown_percent"]:
        reasons.append(f"max drawdown ≥ {GATE['max_drawdown_percent']} %")
    if not _recent(m):
        reasons.append("no trade in the last quarter of the period or the last "
                       f"{GATE['recent_trade_days']} days")
    return not reasons, reasons


def _recent(m: dict) -> bool:
    last, start, end = m.get("latestTradeTime"), m.get("periodFrom"), m.get("periodTo")
    if not last or not end:
        return False
    if end - last <= GATE["recent_trade_days"] * 86_400_000:
        return True
    return bool(start) and last >= start + 0.75 * (end - start)


def _gt(x: Any, v: float) -> bool:
    return x is not None and x == x and x > v


# ─────────────────────────────────────────────────────────────── robust score
def _lin(x: float, lo: float, hi: float) -> float:
    """0 at lo, 100 at hi, clamped (works with lo > hi for 'smaller is better')."""
    if x is None or x != x:
        return 0.0
    if hi == lo:
        return 100.0
    return float(max(0.0, min(100.0, 100.0 * (x - lo) / (hi - lo))))


def consistency(m: dict, equity: list[float], trades: list[dict]) -> float:
    pos_months = _lin(m.get("positiveMonthsPercent"), 30.0, 80.0)
    eq = np.asarray([e for e in equity if e and e > 0], dtype=float)
    if len(eq) > 10 and float(np.std(eq)) > 0:        # a flat curve has no trend to measure
        y = np.log(eq)
        x = np.arange(len(y))
        r = np.corrcoef(x, y)[0, 1]
        slope_up = np.polyfit(x, y, 1)[0] > 0
        linearity = 100.0 * r * r if (r == r and slope_up) else 0.0
        k = max(2, len(eq) // 4)
        step = max(1, len(eq) // 20)
        wins = [eq[i + k - 1] > eq[i] for i in range(0, len(eq) - k + 1, step)]
        rolling = 100.0 * sum(wins) / len(wins) if wins else 0.0
    else:
        linearity = rolling = 0.0
    profits = [t["profit"] for t in trades]
    if len(profits) >= 4:
        h = len(profits) // 2
        a, b = sum(profits[:h]), sum(profits[h:])
        halves = 100.0 if (a > 0 and b > 0) else (40.0 if (a > 0 or b > 0) else 0.0)
    else:
        halves = 0.0
    return 0.3 * pos_months + 0.3 * linearity + 0.2 * halves + 0.2 * rolling


def evidence(m: dict, breadth: float | None) -> float:
    n = m.get("totalTrades") or 0
    trades = 0.0 if n < 20 else min(100.0, 100.0 * math.log(n / 20) / math.log(15))   # 20 → 0, 300 → 100
    months = m.get("monthsTested") or 0
    span = 0.0 if months < 6 else min(100.0, 100.0 * math.log(months / 6) / math.log(10))  # 6 → 0, 60 → 100
    br = 50.0 if breadth is None else 100.0 * breadth
    return 0.5 * trades + 0.2 * span + 0.3 * br


def edge(m: dict) -> float:
    sharpe = _lin(m.get("sharpeRatio"), 0.0, 1.0)            # TradingView's monthly Sharpe
    p = m.get("pValue")
    pval = 0.0 if p is None or p != p else _lin(-math.log10(max(p, 1e-12)), -math.log10(0.5), 3.0)
    pf = m.get("profitFactor")
    pf_s = 100.0 if (pf == math.inf) else _lin(pf, 1.0, 2.5)
    net, bh = m.get("netProfitPercent"), m.get("buyHoldReturnPercent")
    if net is None or net != net:
        alpha = 0.0
    elif bh is None or bh != bh or bh <= 0:
        alpha = 100.0 if net > 0 else 0.0
    else:
        ratio = net / bh
        alpha = _lin(ratio, 0.0, 1.0) * 0.6 if ratio <= 1 else 60.0 + _lin(ratio, 1.0, 2.0) * 0.4
    return 0.3 * sharpe + 0.3 * pval + 0.25 * pf_s + 0.15 * alpha


def practicality(m: dict) -> float:
    dd = _lin(m.get("maxDrawdownPercent"), 60.0, 10.0)
    tpm = m.get("tradesPerMonth")
    if tpm is None or tpm != tpm:
        freq = 0.0
    elif tpm < 1:
        freq = _lin(tpm, 0.1, 1.0)
    elif tpm <= 40:
        freq = 100.0
    else:
        freq = _lin(tpm, 200.0, 40.0)
    cost = _lin(m.get("avgTradePercent"), 0.05, 0.5)
    last, end = m.get("latestTradeTime"), m.get("periodTo")
    days = (end - last) / 86_400_000 if last and end else 9999
    recency = _lin(days, 365.0, 30.0)
    return 0.35 * dd + 0.2 * freq + 0.25 * cost + 0.2 * recency


def robust_score(m: dict, equity: list[float], trades: list[dict], breadth: float | None = None) -> dict:
    c, b, e, p = consistency(m, equity, trades), evidence(m, breadth), edge(m), practicality(m)
    total = round(0.25 * (c + b + e + p))
    return {"robustnessScore": total, "consistency": round(c), "backtests": round(b),
            "edge": round(e), "practicality": round(p)}


def flags(m: dict, trades: list[dict]) -> list[str]:
    """Warnings TradeSearcher calls out instead of featuring (e.g. cherry-picked windows)."""
    out = []
    gross = sum(t["profit"] for t in trades if t["profit"] > 0)
    top = sorted((t["profit"] for t in trades if t["profit"] > 0), reverse=True)[:3]
    if gross > 0 and sum(top) / gross > 0.5 and len(trades) >= 10:
        out.append("concentrated: three trades made over half of the gross profit")
    p = m.get("pValue")
    if p is not None and p == p and p > 0.1:
        out.append("not statistically significant (p > 0.10)")
    if (m.get("totalTrades") or 0) < 100:
        out.append("small sample (< 100 trades)")
    bh = m.get("buyHoldReturnPercent")
    if bh is not None and bh == bh and (m.get("netProfitPercent") or 0) < bh:
        out.append("underperformed buy & hold")
    return out


def weighted_score(robust: float, m: dict) -> float:
    """best-for-symbol ranking: robust score, nudged towards strategies still trading."""
    last, end = m.get("latestTradeTime"), m.get("periodTo")
    days = (end - last) / 86_400_000 if last and end else 9999
    recency = _lin(days, 365.0, 30.0) / 100.0
    return round(robust * (0.85 + 0.15 * recency), 2)
