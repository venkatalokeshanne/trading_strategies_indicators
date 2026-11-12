"""
GMMA Compression Breakout.

Guppy's short (trader) and long (investor) EMA groups overlapping in
price is the classic "compression" read -- both trader and investor
activity are bunched at the same price, a consolidation. When the two
groups separate cleanly with the short group entirely on one side of
the long group, that's a breakout with both timeframes agreeing on
direction.

Entry: the groups were overlapping last bar and are fully separated
this bar, short group above long group (long) or below (short).
Exit: the groups overlap again (momentum faded back into consolidation).

This file contains ONLY strategy logic -- GMMA math lives in
app.indicators.gmma and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.gmma import GuppyMultipleMovingAverage
from app.strategies.registry import strategy_registry

_SHORT_PERIODS = [3, 5, 8, 10, 12, 15]
_LONG_PERIODS = [30, 35, 40, 45, 50, 60]


@strategy_registry.register("gmma_compression_breakout")
class GMMACompressionBreakout(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="gmma_compression_breakout",
            display_name="GMMA Compression Breakout",
            description="Enters when Guppy's short and long EMA groups snap apart cleanly after overlapping -- both trader and investor timeframes agreeing on direction.",
            category="breakout",
            indicators_used=["gmma"],
            default_params={"direction": "both"},
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        self.validate_params(params)
        return GuppyMultipleMovingAverage().calculate(
            df, {"short_periods": _SHORT_PERIODS, "long_periods": _LONG_PERIODS}
        )

    def _group_bounds(self, df: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
        short_cols = [f"gmma_short_ema_{p}" for p in _SHORT_PERIODS]
        long_cols = [f"gmma_long_ema_{p}" for p in _LONG_PERIODS]
        short_max = df[short_cols].max(axis=1)
        short_min = df[short_cols].min(axis=1)
        long_max = df[long_cols].max(axis=1)
        long_min = df[long_cols].min(axis=1)
        return short_max, short_min, long_max, long_min

    def _overlap(self, df: pd.DataFrame) -> pd.Series:
        short_max, short_min, long_max, long_min = self._group_bounds(df)
        return (short_min <= long_max) & (long_min <= short_max)

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        short_max, short_min, long_max, long_min = self._group_bounds(df)
        overlap = self._overlap(df)
        prev_overlap = overlap.shift(1, fill_value=False)

        bullish_separation = short_min > long_max
        bearish_separation = short_max < long_min
        release = prev_overlap & ~overlap

        long_mask = release & bullish_separation
        short_mask = release & bearish_separation

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        return self._overlap(df)
