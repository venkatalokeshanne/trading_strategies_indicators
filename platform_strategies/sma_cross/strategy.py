"""
SMA Cross.

The plainest possible moving-average cross, using classic simple
moving averages at a fast 3/8-period pairing -- deliberately quick to
react (and correspondingly prone to whipsaw), the same short-period
combination popularized by day-trading scalping systems.

Entry: 3-period SMA crosses above 8-period SMA (long); crosses below
(short).
Exit: the next crossover in the opposite direction.

This file contains ONLY strategy logic -- SMA math lives in
app.indicators.sma and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.sma import SMA
from app.strategies.registry import strategy_registry


@strategy_registry.register("sma_cross")
class SMACross(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="sma_cross",
            display_name="SMA Cross",
            description="Classic fast 3/8-period Simple Moving Average cross -- the plainest, quickest-reacting MA cross system.",
            category="trend_following",
            indicators_used=["sma"],
            default_params={"fast_period": 3, "slow_period": 8, "direction": "both"},
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = SMA().calculate(df, {"period": p["fast_period"]})
        out = SMA().calculate(out, {"period": p["slow_period"]})
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        fast, slow = df[f"sma_{p['fast_period']}"], df[f"sma_{p['slow_period']}"]
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
        fast, slow = df[f"sma_{p['fast_period']}"], df[f"sma_{p['slow_period']}"]
        prev_fast, prev_slow = fast.shift(1), slow.shift(1)
        return ((fast > slow) != (prev_fast > prev_slow)) & prev_fast.notna() & prev_slow.notna()
