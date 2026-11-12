"""
SuperTrend Flip.

Trades SuperTrend's own direction flips directly -- one of the most
widely used stop-and-reverse trend tools among day traders because the
line itself doubles as a visual trailing stop.

Entry: SuperTrend's direction flips from down to up (long) or up to
down (short).
Exit: the next flip in the opposite direction.

This file contains ONLY strategy logic -- SuperTrend math lives in
app.indicators.supertrend and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.supertrend import SuperTrend
from app.strategies.registry import strategy_registry


@strategy_registry.register("supertrend_flip")
class SuperTrendFlip(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="supertrend_flip",
            display_name="SuperTrend Flip",
            description="Trades SuperTrend's own direction flips -- the line doubles as its own trailing stop.",
            category="trend_following",
            indicators_used=["supertrend"],
            default_params={"period": 10, "multiple": 3.0, "direction": "both"},
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        return SuperTrend().calculate(df, {"period": p["period"], "multiple": p["multiple"]})

    def _col(self, p: dict[str, Any]) -> str:
        return f"supertrend_direction_{p['period']}_{p['multiple']}"

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        direction = df[self._col(p)]
        prev_direction = direction.shift(1)

        flip_up = (direction == 1) & (prev_direction == -1)
        flip_down = (direction == -1) & (prev_direction == 1)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[flip_up] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[flip_down] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        direction = df[self._col(p)]
        prev_direction = direction.shift(1)
        return (direction != prev_direction) & prev_direction.notna()
