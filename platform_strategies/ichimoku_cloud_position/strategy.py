"""
Ichimoku Cloud Position.

The simplest possible Ichimoku rule, distinct from this library's
`ichimoku_cloud_cross` (which waits for a Tenkan/Kijun cross): trade
purely on which side of the cloud price is on, entering the moment it
crosses fully above or fully below.

Entry: close crosses from inside/below the cloud to fully above it
(long); crosses from inside/above the cloud to fully below it (short).
Exit: close re-enters the cloud from whichever side it broke out of.

This file contains ONLY strategy logic -- Ichimoku math lives in
app.indicators.ichimoku and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.ichimoku import Ichimoku
from app.strategies.registry import strategy_registry


@strategy_registry.register("ichimoku_cloud_position")
class IchimokuCloudPosition(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="ichimoku_cloud_position",
            display_name="Ichimoku Cloud Position",
            description="Trades purely on which side of the Ichimoku cloud price sits -- long above it, short below it.",
            category="trend_following",
            indicators_used=["ichimoku"],
            default_params={
                "conversion_period": 9,
                "base_period": 26,
                "leading_span_b_period": 52,
                "displacement": 26,
                "direction": "both",
            },
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        return Ichimoku().calculate(
            df,
            {
                "conversion_period": p["conversion_period"],
                "base_period": p["base_period"],
                "leading_span_b_period": p["leading_span_b_period"],
                "displacement": p["displacement"],
            },
        )

    def _cloud_bounds(self, df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        span_a, span_b = df["ichimoku_leading_span_a"], df["ichimoku_leading_span_b"]
        both = pd.concat([span_a, span_b], axis=1)
        return both.max(axis=1), both.min(axis=1)

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        cloud_top, cloud_bottom = self._cloud_bounds(df)
        close = df["close"]

        above = close > cloud_top
        below = close < cloud_bottom
        cross_into_above = above & ~above.shift(1, fill_value=False)
        cross_into_below = below & ~below.shift(1, fill_value=False)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[cross_into_above] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[cross_into_below] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        cloud_top, cloud_bottom = self._cloud_bounds(df)
        close = df["close"]

        above = close > cloud_top
        below = close < cloud_bottom
        exit_from_above = ~above & above.shift(1, fill_value=False)
        exit_from_below = ~below & below.shift(1, fill_value=False)
        return exit_from_above | exit_from_below
