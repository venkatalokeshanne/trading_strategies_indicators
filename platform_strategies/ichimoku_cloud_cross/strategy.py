"""
Ichimoku Cloud Cross.

The Tenkan (conversion) / Kijun (base) cross is Ichimoku's own primary
trade trigger; requiring price to already be on the correct side of
the cloud (Senkou spans) at that moment filters crosses that go
against the dominant displaced trend.

Entry: Tenkan crosses above Kijun with price above the cloud (long);
Tenkan crosses below Kijun with price below the cloud (short).
Exit: the opposite Tenkan/Kijun cross.

This file contains ONLY strategy logic -- Ichimoku math lives in
app.indicators.ichimoku and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.ichimoku import Ichimoku
from app.strategies.registry import strategy_registry


@strategy_registry.register("ichimoku_cloud_cross")
class IchimokuCloudCross(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="ichimoku_cloud_cross",
            display_name="Ichimoku Cloud Cross",
            description="Tenkan/Kijun crossovers, taken only in the direction price already sits relative to the Ichimoku cloud.",
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

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        conversion, base = df["ichimoku_conversion"], df["ichimoku_base"]
        span_a, span_b = df["ichimoku_leading_span_a"], df["ichimoku_leading_span_b"]
        close = df["close"]
        prev_conversion, prev_base = conversion.shift(1), base.shift(1)

        cloud_top = pd.concat([span_a, span_b], axis=1).max(axis=1)
        cloud_bottom = pd.concat([span_a, span_b], axis=1).min(axis=1)

        cross_up = (conversion > base) & (prev_conversion <= prev_base) & (close > cloud_top)
        cross_down = (conversion < base) & (prev_conversion >= prev_base) & (close < cloud_bottom)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[cross_up] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[cross_down] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        conversion, base = df["ichimoku_conversion"], df["ichimoku_base"]
        prev_conversion, prev_base = conversion.shift(1), base.shift(1)
        return ((conversion > base) != (prev_conversion > prev_base)) & prev_conversion.notna() & prev_base.notna()
