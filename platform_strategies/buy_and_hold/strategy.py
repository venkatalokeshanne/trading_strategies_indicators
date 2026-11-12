"""
Buy and Hold.

The passive baseline every active strategy should be measured against:
enter long once on the first available bar and never exit on a signal
-- the engine's own end-of-data handling closes the position when the
backtest window runs out. No trend, momentum, or price condition
gates the entry; this is deliberately regime-agnostic.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.strategies.registry import strategy_registry


@strategy_registry.register("buy_and_hold")
class BuyAndHold(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="buy_and_hold",
            display_name="Buy and Hold",
            description="Passive baseline: buy once on the first bar and hold for the entire backtest window, with no exit signal.",
            category="baseline",
            indicators_used=[],
            default_params={},
            entry_conditions=["Once, on the first available bar"],
            exit_conditions=["Never -- only closed by the backtest window ending"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        self.validate_params(params)
        return df.copy()

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        entries = pd.Series(None, index=df.index, dtype=object)
        if len(entries) > 0:
            entries.iloc[0] = TradeDirection.LONG
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        return pd.Series(False, index=df.index)
