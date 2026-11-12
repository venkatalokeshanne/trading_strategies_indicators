"""
Strategy performance metrics: TradingView's Strategy Tester definitions, plus the
statistics TradeSearcher ranks on (risk/reward, t-statistic, p-value, consistency inputs).
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

NA = math.nan


def _safe(a: float, b: float) -> float:
    return a / b if b else NA


# ─────────────────────────────────────────────────────────────── Student t
def _betacf(a: float, b: float, x: float) -> float:
    MAXIT, EPS, FPMIN = 300, 3e-16, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > FPMIN else FPMIN)
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > FPMIN else FPMIN)
        c = 1.0 + aa / c
        c = c if abs(c) > FPMIN else FPMIN
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > FPMIN else FPMIN)
        c = 1.0 + aa / c
        c = c if abs(c) > FPMIN else FPMIN
        de = d * c
        h *= de
        if abs(de - 1.0) < EPS:
            break
    return h


def _betainc(a: float, b: float, x: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(lbeta + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1 - x) / b


def t_test(values: list[float]) -> tuple[float, float]:
    """One-sample t-test of the mean against 0: (t statistic, two-sided p-value)."""
    x = [v for v in values if v == v]
    n = len(x)
    if n < 2:
        return NA, NA
    mean = sum(x) / n
    sd = math.sqrt(sum((v - mean) ** 2 for v in x) / (n - 1))
    if sd == 0:
        return (math.inf if mean > 0 else -math.inf if mean < 0 else NA), (0.0 if mean else NA)
    t = mean / (sd / math.sqrt(n))
    dof = n - 1
    p = _betainc(dof / 2, 0.5, dof / (dof + t * t))
    return t, p


# ─────────────────────────────────────────────────────────────── main
def compute(res: Any) -> dict[str, Any]:
    """All metrics for a strategy RunResult."""
    b = res.broker
    if b is None:
        raise ValueError("metrics need a strategy run")
    cfg = b.cfg
    init = cfg.initial_capital
    closed = b.closed
    bars = res.bars
    times = bars["time"].to_numpy(dtype=np.int64)
    n = len(times)

    profits = [t.profit for t in closed]
    pct = [t.profit_percent for t in closed]
    wins = [t for t in closed if t.profit > 0]
    losses = [t for t in closed if t.profit < 0]
    gp = sum(t.profit for t in wins)
    gl = -sum(t.profit for t in losses)
    net = b.netprofit

    avg_win = _safe(gp, len(wins))
    avg_loss = _safe(-gl, len(losses))
    eq_close = np.asarray(b.equity_close, dtype=float)
    eq_worst = np.asarray(b.equity_worst, dtype=float)
    eq_best = np.asarray(b.equity_best, dtype=float)

    dd_close, dd_close_pct = _max_drawdown(eq_close, eq_close)
    dd_intra, dd_intra_pct = _max_drawdown(eq_best, eq_worst)
    runup, runup_pct = _max_runup(eq_close)

    first_close = float(bars["close"].iloc[0]) if n else NA
    last_close = float(bars["close"].iloc[-1]) if n else NA
    bh_pct = 100.0 * (last_close / first_close - 1.0) if first_close else NA   # [VERIFY] TV's start bar

    monthly = _monthly_returns(times, eq_close, res.symbol.timezone)
    rfr_m = cfg.risk_free_rate / 100.0 / 12.0
    sharpe = sortino = NA
    if len(monthly) >= 2:
        mr = float(np.mean(monthly))
        sd = float(np.std(monthly))                      # [VERIFY] population vs sample
        sharpe = _safe(mr - rfr_m, sd)
        downside = np.minimum(np.asarray(monthly) - rfr_m, 0.0)
        dd = float(math.sqrt(np.mean(downside ** 2)))
        sortino = _safe(mr - rfr_m, dd)

    t_stat, p_value = t_test(pct)
    in_market = int(np.count_nonzero(np.asarray(b.position_curve) != 0)) if b.position_curve else 0
    span_days = (times[-1] - times[0]) / 86_400_000 if n > 1 else 0.0
    months = span_days / 30.4375 if span_days else NA
    final_equity = float(eq_close[-1]) if len(eq_close) else init
    years = span_days / 365.25 if span_days else NA
    cagr = (final_equity / init) ** (1 / years) - 1 if years and years > 0 and final_equity > 0 else NA
    streak_w, streak_l = _streaks(profits)

    return {
        "initialCapital": init,
        "netProfit": net,
        "netProfitPercent": 100.0 * net / init,
        "grossProfit": gp,
        "grossLoss": gl,
        "profitFactor": (math.inf if gp > 0 else NA) if gl == 0 else gp / gl,
        "totalTrades": len(closed),
        "openTrades": len(b.open),
        "winningTrades": len(wins),
        "losingTrades": len(losses),
        "evenTrades": len(closed) - len(wins) - len(losses),
        "percentProfitable": _safe(100.0 * len(wins), len(closed)),
        "avgTrade": _safe(net, len(closed)),
        "avgTradePercent": float(np.mean(pct)) if pct else NA,
        "avgWinningTrade": avg_win,
        "avgWinningTradePercent": float(np.mean([t.profit_percent for t in wins])) if wins else NA,
        "avgLosingTrade": avg_loss,
        "avgLosingTradePercent": float(np.mean([t.profit_percent for t in losses])) if losses else NA,
        "riskReward": _safe(avg_win, abs(avg_loss)) if avg_loss == avg_loss else NA,
        "largestWinningTrade": max(profits) if profits and max(profits) > 0 else NA,
        "largestLosingTrade": min(profits) if profits and min(profits) < 0 else NA,
        "largestWinningTradePercent": max(pct) if pct else NA,
        "largestLosingTradePercent": min(pct) if pct else NA,
        "avgBarsInTrade": float(np.mean([t.bars for t in closed])) if closed else NA,
        "avgBarsInWinningTrade": float(np.mean([t.bars for t in wins])) if wins else NA,
        "avgBarsInLosingTrade": float(np.mean([t.bars for t in losses])) if losses else NA,
        "maxDrawdown": dd_intra,
        "maxDrawdownPercent": dd_intra_pct,
        "maxDrawdownClose": dd_close,
        "maxDrawdownClosePercent": dd_close_pct,
        "maxRunup": runup,
        "maxRunupPercent": runup_pct,
        "buyHoldReturnPercent": bh_pct,
        "sharpeRatio": sharpe,
        "sortinoRatio": sortino,
        "commissionPaid": b.commission_paid,
        "maxContractsHeld": b.max_contracts,
        "openProfit": b.openprofit(last_close) if n else 0.0,
        "tStat": t_stat,
        "pValue": p_value,
        "expectancyPercent": float(np.mean(pct)) if pct else NA,
        "maxConsecutiveWins": streak_w,
        "maxConsecutiveLosses": streak_l,
        "exposurePercent": 100.0 * in_market / n if n else NA,
        "tradesPerMonth": _safe(len(closed), months) if months == months else NA,
        "cagrPercent": 100.0 * cagr if cagr == cagr else NA,
        "calmar": _safe(100.0 * cagr, dd_intra_pct) if cagr == cagr else NA,
        "recoveryFactor": _safe(net, dd_intra),
        "monthsTested": months,
        "positiveMonthsPercent": 100.0 * sum(1 for r in monthly if r > 0) / len(monthly) if monthly else NA,
        "firstTradeTime": closed[0].entry_time if closed else None,
        "latestTradeTime": max(t.exit_time for t in closed) if closed else None,
        "periodFrom": int(times[0]) if n else None,
        "periodTo": int(times[-1]) if n else None,
    }


def _max_drawdown(peak_src: np.ndarray, trough_src: np.ndarray) -> tuple[float, float]:
    if len(peak_src) == 0:
        return 0.0, 0.0
    peak = -math.inf
    best, best_pct = 0.0, 0.0
    for hi, lo in zip(peak_src, trough_src):
        # the trough of THIS bar is measured against the peak reached BEFORE it
        dd = peak - lo if peak != -math.inf else 0.0
        if dd > best:
            best = dd
            best_pct = 100.0 * dd / peak if peak > 0 else NA
        peak = max(peak, hi)
    return best, best_pct


def _max_runup(eq: np.ndarray) -> tuple[float, float]:
    if len(eq) == 0:
        return 0.0, 0.0
    trough = math.inf
    best, best_pct = 0.0, 0.0
    for v in eq:
        trough = min(trough, v)
        ru = v - trough
        if ru > best:
            best = ru
            best_pct = 100.0 * ru / trough if trough > 0 else NA
    return best, best_pct


def _monthly_returns(times: np.ndarray, eq: np.ndarray, tz: str) -> list[float]:
    if len(eq) == 0:
        return []
    idx = pd.to_datetime(times, unit="ms", utc=True).tz_convert(tz)
    s = pd.Series(eq, index=idx)
    month_end = s.groupby([idx.year, idx.month]).last()
    vals = month_end.to_numpy(dtype=float)
    start = float(eq[0])
    prevs = np.concatenate([[start], vals[:-1]])
    return [float(v / p - 1.0) for v, p in zip(vals, prevs) if p]


def _streaks(profits: list[float]) -> tuple[int, int]:
    bw = bl = cw = cl = 0
    for p in profits:
        if p > 0:
            cw += 1; cl = 0
        elif p < 0:
            cl += 1; cw = 0
        else:
            cw = cl = 0
        bw, bl = max(bw, cw), max(bl, cl)
    return bw, bl


def curves(res: Any, points: int | None = None) -> dict[str, list]:
    """Equity, drawdown and buy-and-hold curves (optionally down-sampled)."""
    b = res.broker
    times = res.bars["time"].tolist()
    eq = list(b.equity_close)
    init = b.cfg.initial_capital
    peak, dd = -math.inf, []
    for v in eq:
        peak = max(peak, v)
        dd.append(100.0 * (v - peak) / peak if peak > 0 else 0.0)
    c0 = res.bars["close"].iloc[0]
    bh = [init * c / c0 for c in res.bars["close"].tolist()]
    out = {"time": times, "equity": eq, "drawdownPercent": dd, "buyHold": bh}
    if points and len(times) > points:
        step = len(times) / points
        idx = sorted({int(k * step) for k in range(points)} | {len(times) - 1})
        out = {k: [v[i] for i in idx] for k, v in out.items()}
    return out


def trades_table(res: Any) -> list[dict]:
    """TradingView's 'List of trades', one row per closed (part of a) trade."""
    rows = []
    cum = 0.0
    for k, t in enumerate(res.broker.closed, start=1):
        cum += t.profit
        rows.append({
            "n": k, "type": "long" if t.direction > 0 else "short",
            "entry": {"id": t.entry_id, "time": t.entry_time, "price": t.entry_price, "bar": t.entry_bar},
            "exit": {"id": t.exit_comment or t.exit_id, "time": t.exit_time, "price": t.exit_price, "bar": t.exit_bar},
            "qty": t.qty, "profit": t.profit, "profitPercent": t.profit_percent,
            "cumulativeProfit": cum, "runUp": t.run_up, "drawdown": t.drawdown,
            "commission": t.commission, "bars": t.bars,
        })
    return rows
