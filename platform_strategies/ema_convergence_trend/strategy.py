"""
EMA Convergence Trend.

Three EMAs (fast/mid/slow) tightly converging -- their spread within a
small % threshold -- while all three sit on the same side of a longer
trend EMA, reads as a "coiled" trend-continuation setup: the shorter
averages have caught up to and aligned with the longer-term trend
rather than diverging from it.

Entry: fires on the bar the convergence+alignment condition first
becomes true (long: all 3 fast EMAs above the trend EMA; short: all 3
below).
Exit: the alignment that triggered the trade breaks (any of the 3
fast EMAs no longer converged, or no longer aligned with the trend
EMA).

This file contains ONLY strategy logic -- EMA math lives in
app.indicators.ema and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.ema import EMA
from app.strategies.registry import strategy_registry


@strategy_registry.register("ema_convergence_trend")
class EMAConvergenceTrend(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="ema_convergence_trend",
            display_name="EMA Convergence Trend",
            description="3 fast EMAs converge tightly while all aligned on one side of a trend EMA -- a coiled trend-continuation setup.",
            category="trend_following",
            indicators_used=["ema"],
            default_params={
                "fast_period": 10,
                "mid_period": 20,
                "slow_period": 89,
                "trend_period": 200,
                "convergence_threshold_pct": 1.0,
                "direction": "both",
            },
            entry_conditions=[
                "Long: fast/mid/slow EMAs converge within convergence_threshold_pct of each other AND all sit above the trend EMA",
                "Short: same convergence, all 3 below the trend EMA",
            ],
            exit_conditions=["The triggering alignment breaks (loses convergence or crosses the trend EMA)"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = df
        for period in (p["fast_period"], p["mid_period"], p["slow_period"], p["trend_period"]):
            out = EMA().calculate(out, {"period": period, "source": "close"})
        return out

    def _conditions(self, df: pd.DataFrame, p: dict[str, Any]) -> tuple[pd.Series, pd.Series]:
        fast, mid, slow = df[f"ema_{p['fast_period']}"], df[f"ema_{p['mid_period']}"], df[f"ema_{p['slow_period']}"]
        trend = df[f"ema_{p['trend_period']}"]

        highest = pd.concat([fast, mid, slow], axis=1).max(axis=1)
        lowest = pd.concat([fast, mid, slow], axis=1).min(axis=1)
        spread_pct = (highest - lowest) / lowest * 100
        is_converged = spread_pct <= p["convergence_threshold_pct"]

        all_above = (fast > trend) & (mid > trend) & (slow > trend)
        all_below = (fast < trend) & (mid < trend) & (slow < trend)

        buy_condition = is_converged & all_above
        sell_condition = is_converged & all_below
        return buy_condition, sell_condition

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        buy_condition, sell_condition = self._conditions(df, p)
        buy_signal = buy_condition & ~buy_condition.shift(1).fillna(False).infer_objects(copy=False).astype(bool)
        sell_signal = sell_condition & ~sell_condition.shift(1).fillna(False).infer_objects(copy=False).astype(bool)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[buy_signal] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[sell_signal] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        buy_condition, sell_condition = self._conditions(df, p)
        buy_broke = buy_condition.shift(1).fillna(False).infer_objects(copy=False).astype(bool) & ~buy_condition
        sell_broke = sell_condition.shift(1).fillna(False).infer_objects(copy=False).astype(bool) & ~sell_condition
        return buy_broke | sell_broke
