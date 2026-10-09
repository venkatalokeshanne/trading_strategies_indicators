"""
TradeSearcher's free calculators, as pure functions (inputs → JSON-ready dict).

Exact formulas where a closed form exists; seeded Monte Carlo elsewhere (results are
reproducible for the same inputs and seed).
"""

from __future__ import annotations

import math
import random
import statistics
from typing import Any


def _pct(x: float) -> float:
    return x / 100.0


def _percentiles(v: list[float], ps=(5, 25, 50, 75, 95)) -> dict:
    s = sorted(v)
    n = len(s)
    return {f"p{p}": s[min(n - 1, max(0, int(round(p / 100 * (n - 1)))))] for p in ps} if n else {}


# 1 ─────────────────────────────────────────────────────────────── profit
def trading_strategy_profit(capital: float, trades_per_month: float, win_rate: float, avg_win_percent: float,
                            avg_loss_percent: float, months: int = 12, compounding: bool = True) -> dict:
    """Expected path from per-trade expectancy (avg win/loss as % of equity risked per trade)."""
    w = _pct(win_rate)
    exp_pct = w * avg_win_percent - (1 - w) * abs(avg_loss_percent)
    eq, path = capital, []
    for m in range(1, months + 1):
        n = trades_per_month
        eq = eq * (1 + exp_pct / 100) ** n if compounding else eq + capital * exp_pct / 100 * n
        path.append({"month": m, "equity": round(eq, 2)})
    return {"expectancyPercentPerTrade": exp_pct, "finalEquity": round(eq, 2),
            "totalReturnPercent": round(100 * (eq / capital - 1), 4), "path": path}


# 2 ─────────────────────────────────────────────────────────────── equity simulation
def equity_curve_simulation(capital: float, win_rate: float, reward_risk: float, risk_percent: float,
                            trades: int = 200, runs: int = 1000, seed: int = 1, curves: int = 20) -> dict:
    rng = random.Random(seed)
    w, r = _pct(win_rate), _pct(risk_percent)
    finals, dds, samples = [], [], []
    for k in range(runs):
        eq, peak, mdd, path = capital, capital, 0.0, [capital]
        for _ in range(trades):
            risk = eq * r
            eq += risk * reward_risk if rng.random() < w else -risk
            peak = max(peak, eq)
            mdd = max(mdd, (peak - eq) / peak if peak else 0)
            if k < curves:
                path.append(round(eq, 2))
        finals.append(eq)
        dds.append(100 * mdd)
        if k < curves:
            samples.append(path)
    return {"finalEquity": _percentiles(finals), "maxDrawdownPercent": _percentiles(dds),
            "probabilityOfLoss": sum(1 for f in finals if f < capital) / runs,
            "medianReturnPercent": 100 * (statistics.median(finals) / capital - 1), "sampleCurves": samples}


# 3 ─────────────────────────────────────────────────────────────── risk / reward
def risk_reward(entry: float, stop: float, target: float) -> dict:
    risk, reward = abs(entry - stop), abs(target - entry)
    rr = reward / risk if risk else math.inf
    return {"risk": risk, "reward": reward, "riskReward": rr,
            "breakevenWinRate": 100 / (1 + rr) if rr != math.inf else 0.0,
            "direction": "long" if target > entry else "short"}


# 4 ─────────────────────────────────────────────────────────────── risk of ruin
def risk_of_ruin(win_rate: float, reward_risk: float, risk_percent: float, ruin_drawdown_percent: float = 50,
                 trades: int = 1000, runs: int = 2000, seed: int = 1) -> dict:
    """Probability that fixed-fractional risking hits a drawdown of ``ruin_drawdown_percent``."""
    rng = random.Random(seed)
    w, r, ruin = _pct(win_rate), _pct(risk_percent), _pct(ruin_drawdown_percent)
    hit = 0
    for _ in range(runs):
        eq = peak = 1.0
        for _ in range(trades):
            eq *= (1 + r * reward_risk) if rng.random() < w else (1 - r)
            peak = max(peak, eq)
            if eq <= peak * (1 - ruin):
                hit += 1
                break
    edge = w * reward_risk - (1 - w)
    return {"riskOfRuinPercent": 100 * hit / runs, "edgePerTradeR": edge,
            "note": "Monte Carlo over the given number of trades, fixed-fractional risk"}


# 5 ─────────────────────────────────────────────────────────────── loss recovery
def loss_recovery(loss_percent: float) -> dict:
    L = _pct(loss_percent)
    need = math.inf if L >= 1 else 100 * (1 / (1 - L) - 1)
    return {"lossPercent": loss_percent, "gainNeededPercent": need,
            "table": [{"loss": x, "gainNeeded": round(100 * (1 / (1 - x / 100) - 1), 2)} for x in (5, 10, 20, 30, 50, 75)]}


# 6 ─────────────────────────────────────────────────────────────── losing streaks
def losing_streak(win_rate: float, trades: int, streak: int) -> dict:
    """Exact probability of at least one run of ``streak`` consecutive losses in ``trades``."""
    q = 1 - _pct(win_rate)
    # dp[j] = P(no qualifying run so far and current loss run == j)
    dp = [0.0] * streak
    dp[0] = 1.0
    for _ in range(trades):
        new = [0.0] * streak
        new[0] = sum(dp) * (1 - q)
        for j in range(streak - 1):
            new[j + 1] = dp[j] * q
        dp = new
    p_at_least = 1 - sum(dp)
    expected_longest = math.log(trades * (1 - q)) / math.log(1 / q) if 0 < q < 1 and trades * (1 - q) > 1 else None
    return {"probabilityPercent": 100 * p_at_least, "expectedLongestLosingStreak": expected_longest}


# 7 ─────────────────────────────────────────────────────────────── profit factor
def profit_factor(gross_profit: float | None = None, gross_loss: float | None = None,
                  win_rate: float | None = None, reward_risk: float | None = None) -> dict:
    if gross_profit is not None and gross_loss is not None:
        pf = gross_profit / abs(gross_loss) if gross_loss else math.inf
    else:
        w = _pct(win_rate)
        pf = (w * reward_risk) / (1 - w) if w < 1 else math.inf
    grade = "excellent" if pf >= 2 else "good" if pf >= 1.5 else "marginal" if pf >= 1.1 else "losing" if pf < 1 else "breakeven"
    return {"profitFactor": pf, "assessment": grade}


# 8, 9, 15 ───────────────────────────────────────────────────────── prop firms
def prop_firm_payout(profit: float, profit_split_percent: float = 80, fees: float = 0.0,
                     refund_fee_on_first_payout: bool = True) -> dict:
    trader = profit * _pct(profit_split_percent)
    return {"traderPayout": trader + (fees if refund_fee_on_first_payout else 0.0),
            "firmShare": profit - trader, "netAfterFees": trader - (0 if refund_fee_on_first_payout else fees)}


def prop_firm_consistency(daily_profits: list[float], max_best_day_percent: float = 30.0) -> dict:
    total = sum(p for p in daily_profits)
    best = max(daily_profits) if daily_profits else 0.0
    share = 100 * best / total if total > 0 else math.inf
    need = best / _pct(max_best_day_percent) - total if share > max_best_day_percent else 0.0
    return {"bestDayShare": share, "passes": share <= max_best_day_percent, "additionalProfitNeeded": max(0.0, need)}


def prop_firm_challenge(profit_target_percent: float, max_drawdown_percent: float, daily_drawdown_percent: float,
                        win_rate: float, reward_risk: float, risk_percent: float, trades_per_day: int = 2,
                        max_days: int = 30, runs: int = 3000, seed: int = 1, trailing: bool = False) -> dict:
    rng = random.Random(seed)
    w = _pct(win_rate)
    passed = failed_dd = failed_daily = timeout = 0
    days_to_pass = []
    for _ in range(runs):
        eq = peak = 1.0
        outcome = None
        for d in range(1, max_days + 1):
            day_start = eq
            for _ in range(trades_per_day):
                risk = _pct(risk_percent) * (1.0 if not trailing else eq)
                eq += risk * reward_risk if rng.random() < w else -risk
                peak = max(peak, eq)
                floor = (peak if trailing else 1.0) * (1 - _pct(max_drawdown_percent))
                if eq <= floor:
                    outcome = "dd"; break
                if eq <= day_start * (1 - _pct(daily_drawdown_percent)):
                    outcome = "daily"; break
                if eq >= 1 + _pct(profit_target_percent):
                    outcome = "pass"; break
            if outcome:
                break
        if outcome == "pass":
            passed += 1; days_to_pass.append(d)
        elif outcome == "dd":
            failed_dd += 1
        elif outcome == "daily":
            failed_daily += 1
        else:
            timeout += 1
    return {"passProbabilityPercent": 100 * passed / runs, "failMaxDrawdownPercent": 100 * failed_dd / runs,
            "failDailyDrawdownPercent": 100 * failed_daily / runs, "timeoutPercent": 100 * timeout / runs,
            "medianDaysToPass": statistics.median(days_to_pass) if days_to_pass else None}


# 10 ─────────────────────────────────────────────────────────────── SL / TP
def stop_loss_take_profit(entry: float, direction: str = "long", stop_percent: float | None = None,
                          atr: float | None = None, atr_multiple: float = 1.5, reward_risk: float = 2.0) -> dict:
    dist = entry * _pct(stop_percent) if stop_percent is not None else (atr or 0) * atr_multiple
    sgn = 1 if direction == "long" else -1
    return {"stop": entry - sgn * dist, "target": entry + sgn * dist * reward_risk, "riskPerUnit": dist}


# 11 ─────────────────────────────────────────────────────────────── average down
def average_down(positions: list[dict], current_price: float | None = None) -> dict:
    qty = sum(p["qty"] for p in positions)
    cost = sum(p["qty"] * p["price"] for p in positions)
    avg = cost / qty if qty else None
    out = {"totalQty": qty, "averagePrice": avg, "totalCost": cost}
    if current_price is not None and avg:
        out["unrealisedPnl"] = (current_price - avg) * qty
        out["unrealisedPercent"] = 100 * (current_price / avg - 1)
    return out


# 12 ─────────────────────────────────────────────────────────────── Sharpe
def sharpe_ratio(returns_percent: list[float], risk_free_percent_per_year: float = 2.0,
                 periods_per_year: int = 12) -> dict:
    r = [x / 100 for x in returns_percent]
    if len(r) < 2:
        return {"sharpe": None, "sortino": None}
    rf = _pct(risk_free_percent_per_year) / periods_per_year
    ex = [x - rf for x in r]
    mean, sd = statistics.mean(ex), statistics.stdev(r)
    dd = math.sqrt(sum(min(0, x) ** 2 for x in ex) / len(ex))
    k = math.sqrt(periods_per_year)
    return {"sharpe": mean / sd * k if sd else None, "sortino": mean / dd * k if dd else None,
            "periodSharpe": mean / sd if sd else None}


# 13 ─────────────────────────────────────────────────────────────── Kelly
def kelly_criterion(win_rate: float, reward_risk: float, fraction: float = 1.0, trades: int = 500,
                    runs: int = 500, seed: int = 1) -> dict:
    w = _pct(win_rate)
    k = w - (1 - w) / reward_risk
    rng = random.Random(seed)
    sims = {}
    for f in (0.25, 0.5, 1.0):
        bet = max(0.0, k * f)
        finals = []
        for _ in range(runs):
            eq = 1.0
            for _ in range(trades):
                eq *= (1 + bet * reward_risk) if rng.random() < w else (1 - bet)
            finals.append(eq)
        sims[f"{f:g}x"] = {"riskPercent": 100 * bet, "medianGrowth": statistics.median(finals)}
    return {"kellyPercent": 100 * k, "recommendedPercent": 100 * max(0.0, k * fraction), "simulation": sims}


# 14 ─────────────────────────────────────────────────────────────── lot size
def lot_size(account: float, risk_percent: float, stop_distance: float, value_per_point: float = 1.0,
             contract_size: float = 1.0) -> dict:
    risk_amount = account * _pct(risk_percent)
    per_unit = stop_distance * value_per_point * contract_size
    units = risk_amount / per_unit if per_unit else 0.0
    return {"riskAmount": risk_amount, "positionSize": units,
            "standardLots": units / 100_000 if contract_size == 1 else None}


# 16 ─────────────────────────────────────────────────────────────── expectancy
def trading_expectancy(win_rate: float, avg_win: float, avg_loss: float) -> dict:
    w = _pct(win_rate)
    e = w * avg_win - (1 - w) * abs(avg_loss)
    return {"expectancyPerTrade": e, "expectancyR": e / abs(avg_loss) if avg_loss else None,
            "breakevenWinRate": 100 * abs(avg_loss) / (avg_win + abs(avg_loss)) if (avg_win + abs(avg_loss)) else None}


# 17 ─────────────────────────────────────────────────────────────── compounding
def trading_compounding(capital: float, return_percent_per_period: float, periods: int,
                        contribution_per_period: float = 0.0) -> dict:
    eq, path = capital, []
    for k in range(1, periods + 1):
        eq = eq * (1 + _pct(return_percent_per_period)) + contribution_per_period
        path.append(round(eq, 2))
    invested = capital + contribution_per_period * periods
    return {"finalEquity": eq, "invested": invested, "profit": eq - invested, "path": path}


# 18 ─────────────────────────────────────────────────────────────── report card
def strategy_performance_metrics(pnls: list[float], starting_capital: float = 10_000.0) -> dict:
    """Grade a list of per-trade P&L values (the 'paste your trades' tool)."""
    from pinelib.metrics import t_test
    if not pnls:
        return {"error": "no trades"}
    wins = [p for p in pnls if p > 0]
    losses = [-p for p in pnls if p < 0]
    gp, gl = sum(wins), sum(losses)
    eq, peak, mdd = starting_capital, starting_capital, 0.0
    for p in pnls:
        eq += p
        peak = max(peak, eq)
        mdd = max(mdd, (peak - eq) / peak if peak else 0)
    pf = gp / gl if gl else math.inf
    wr = 100 * len(wins) / len(pnls)
    t, pv = t_test(pnls)
    score = (min(pf, 3) / 3 * 35 + min(wr, 70) / 70 * 15 + max(0, 1 - mdd / 0.5) * 30
             + (20 if pv == pv and pv < 0.05 else 10 if pv == pv and pv < 0.2 else 0))
    grade = "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 50 else "D" if score >= 35 else "F"
    streak = cur = 0
    for p in pnls:
        cur = cur + 1 if p < 0 else 0
        streak = max(streak, cur)
    return {"trades": len(pnls), "netProfit": sum(pnls), "profitFactor": pf, "winRate": wr,
            "avgWin": gp / len(wins) if wins else 0.0, "avgLoss": gl / len(losses) if losses else 0.0,
            "riskReward": (gp / len(wins)) / (gl / len(losses)) if wins and losses else None,
            "maxDrawdownPercent": 100 * mdd, "longestLosingStreak": streak,
            "expectancy": sum(pnls) / len(pnls), "tStat": t, "pValue": pv, "score": round(score, 1), "grade": grade}


CALCULATORS: dict[str, Any] = {
    "trading-strategy-profit-calculator": trading_strategy_profit,
    "trading-equity-curve-simulation": equity_curve_simulation,
    "risk-reward-calculator": risk_reward,
    "risk-of-ruin-calculator": risk_of_ruin,
    "loss-recovery-calculator": loss_recovery,
    "losing-streak-calculator": losing_streak,
    "profit-factor-calculator": profit_factor,
    "prop-firm-payout-calculator": prop_firm_payout,
    "prop-firm-consistency-calculator": prop_firm_consistency,
    "stop-loss-take-profit-calculator": stop_loss_take_profit,
    "average-down-calculator": average_down,
    "sharpe-ratio-calculator": sharpe_ratio,
    "kelly-criterion-simulator": kelly_criterion,
    "lot-size-calculator": lot_size,
    "prop-firm-challenge-calculator": prop_firm_challenge,
    "trading-expectancy-calculator": trading_expectancy,
    "trading-compounding-calculator": trading_compounding,
    "strategy-performance-metrics": strategy_performance_metrics,
}
