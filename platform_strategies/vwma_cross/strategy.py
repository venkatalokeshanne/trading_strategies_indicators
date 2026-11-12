"""
VWMA Cross.

A fast/slow moving-average cross built on Volume Weighted Moving
Averages instead of plain EMAs/SMAs: because VWMA already weights each
bar by its own volume, a cross only carries weight when it was driven
by genuinely well-traded bars, giving a built-in volume filter without
a separate volume check.

Entry: fast VWMA crosses above (long) / below (short) slow VWMA.
Exit: the next crossover in the opposite direction.

This file contains ONLY strategy logic -- VWMA math lives in
app.indicators.vwma and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.vwma import VolumeWeightedMovingAverage
from app.strategies.registry import strategy_registry


@strategy_registry.register("vwma_cross")
class VWMACross(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="vwma_cross",
            display_name="VWMA Cross",
            description="Fast/slow Volume Weighted Moving Average cross -- volume-driven crosses only, since VWMA already discounts thin bars.",
            category="trend_following",
            indicators_used=["vwma"],
            default_params={"fast_period": 10, "slow_period": 30, "direction": "both"},
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = VolumeWeightedMovingAverage().calculate(df, {"period": p["fast_period"]})
        out = VolumeWeightedMovingAverage().calculate(out, {"period": p["slow_period"]})
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        fast, slow = df[f"vwma_{p['fast_period']}"], df[f"vwma_{p['slow_period']}"]
        prev_fast, prev_slow = fast.shift(1), slow.shift(1)

        cross_up = (fast > slow) & (prev_fast <= prev_slow)
        cross_down = (fast < slow) & (prev_fast >= prev_slow)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[cross_up] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[cross_down] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        fast, slow = df[f"vwma_{p['fast_period']}"], df[f"vwma_{p['slow_period']}"]
        prev_fast, prev_slow = fast.shift(1), slow.shift(1)
        return ((fast > slow) != (prev_fast > prev_slow)) & prev_fast.notna() & prev_slow.notna()
