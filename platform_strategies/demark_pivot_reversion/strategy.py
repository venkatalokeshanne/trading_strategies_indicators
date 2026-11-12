"""
DeMark Pivot Reversion.

DeMark's pivot formula only produces a single resistance and support
level (no R2/R3 tiers like classic or Camarilla pivots), derived from
whether the prior session closed above, below, or at its own open --
a different, conditional read on the prior day than the other two
pivot families use. Trades a rejection at either level, targeting
reversion back to the DeMark pivot itself.

Entry: price touches/exceeds DeMark resistance and closes back below
it (short); touches/dips below DeMark support and closes back above it
(long).
Exit: price reverts back to the DeMark pivot.

This file contains ONLY strategy logic -- DeMark Pivot math lives in
app.indicators.demark_pivots and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.demark_pivots import DeMarkPivots
from app.strategies.registry import strategy_registry


@strategy_registry.register("demark_pivot_reversion")
class DeMarkPivotReversion(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="demark_pivot_reversion",
            display_name="DeMark Pivot Reversion",
            description="Fades a rejection at DeMark's resistance/support level, targeting reversion back to the DeMark pivot.",
            category="mean_reversion",
            indicators_used=["demark_pivots"],
            default_params={"direction": "both"},
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        self.validate_params(params)
        return DeMarkPivots().calculate(df, {})

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        resistance, support = df["demark_resistance"], df["demark_support"]
        high, low, close = df["high"], df["low"], df["close"]

        short_mask = (high >= resistance) & (close < resistance)
        long_mask = (low <= support) & (close > support)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        pivot, close = df["demark_pivot"], df["close"]
        prev_close, prev_pivot = close.shift(1), pivot.shift(1)
        return ((close > pivot) != (prev_close > prev_pivot)) & prev_pivot.notna()
