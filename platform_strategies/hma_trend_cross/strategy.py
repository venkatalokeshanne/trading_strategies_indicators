"""
HMA Trend Cross.

A faster, less-laggy alternative to a plain EMA cross: Hull's Moving
Average reacts to price changes with noticeably less delay than an
EMA/SMA of the same period, so a fast/slow HMA cross catches trend
changes earlier -- at the cost of being a bit more prone to whipsaw in
truly choppy conditions. Volume confirmation (on by default) filters
out the weakest crosses.

Entry: fast HMA crosses above (long) / below (short) slow HMA, with
volume above its rolling average.
Exit: the next crossover in the opposite direction.

This file contains ONLY strategy logic -- HMA/volume math lives in
app.indicators and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.filters.volume_above_average import VolumeAboveAverage
from app.indicators.hma import HullMovingAverage
from app.indicators.volume_average import VolumeAverage
from app.strategies.registry import strategy_registry


@strategy_registry.register("hma_trend_cross")
class HMATrendCross(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="hma_trend_cross",
            display_name="HMA Trend Cross",
            description="Fast/slow Hull Moving Average cross -- reacts faster than a plain EMA cross with less lag.",
            category="trend_following",
            indicators_used=["hma", "volume_average"],
            default_params={
                "fast_period": 9,
                "slow_period": 21,
                "use_volume_filter": True,
                "volume_avg_period": 20,
                "direction": "both",
            },
            entry_conditions=[
                "Long: fast HMA crosses above slow HMA",
                "Short: fast HMA crosses below slow HMA",
                "(optional, on by default) volume is above its rolling average",
            ],
            exit_conditions=["The next HMA crossover in the opposite direction"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = HullMovingAverage().calculate(df, {"period": p["fast_period"]})
        out = HullMovingAverage().calculate(out, {"period": p["slow_period"]})
        if p["use_volume_filter"]:
            out = VolumeAverage().calculate(out, {"period": p["volume_avg_period"]})
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        fast, slow = df[f"hma_{p['fast_period']}"], df[f"hma_{p['slow_period']}"]
        prev_fast, prev_slow = fast.shift(1), slow.shift(1)

        cross_up = (fast > slow) & (prev_fast <= prev_slow)
        cross_down = (fast < slow) & (prev_fast >= prev_slow)

        if p["use_volume_filter"]:
            volume_confirmed = VolumeAboveAverage().apply(df, {"period": p["volume_avg_period"]})
            cross_up = cross_up & volume_confirmed
            cross_down = cross_down & volume_confirmed

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[cross_up] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[cross_down] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        fast, slow = df[f"hma_{p['fast_period']}"], df[f"hma_{p['slow_period']}"]
        prev_fast, prev_slow = fast.shift(1), slow.shift(1)
        return ((fast > slow) != (prev_fast > prev_slow)) & prev_fast.notna() & prev_slow.notna()
