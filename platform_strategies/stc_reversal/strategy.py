"""
STC Reversal.

Schaff Trend Cycle oscillates between 0 and 100 much like a stochastic.
Trades the classic oscillator-reversal read: STC turning up out of its
oversold zone signals a fresh bullish swing, turning down out of its
overbought zone signals a fresh bearish swing. Because STC is
double-smoothed MACD, these turns tend to lead a plain MACD cross.

Entry: STC crosses back above the oversold level (long) or back below
the overbought level (short).
Exit: STC crosses the opposite extreme zone.

This file contains ONLY strategy logic -- STC math lives in
app.indicators.stc and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.stc import SchaffTrendCycle
from app.strategies.registry import strategy_registry


@strategy_registry.register("stc_reversal")
class STCReversal(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="stc_reversal",
            display_name="STC Reversal",
            description="Trades Schaff Trend Cycle turning out of its oversold/overbought zones -- an early, double-smoothed MACD turn signal.",
            category="momentum",
            indicators_used=["stc"],
            default_params={
                "fast_period": 23,
                "slow_period": 50,
                "cycle_period": 10,
                "d1_period": 3,
                "d2_period": 3,
                "oversold": 25.0,
                "overbought": 75.0,
                "direction": "both",
            },
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        return SchaffTrendCycle().calculate(
            df,
            {
                "fast_period": p["fast_period"],
                "slow_period": p["slow_period"],
                "cycle_period": p["cycle_period"],
                "d1_period": p["d1_period"],
                "d2_period": p["d2_period"],
            },
        )

    def _col(self, p: dict[str, Any]) -> str:
        return f"stc_{p['cycle_period']}"

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        stc = df[self._col(p)]
        prev = stc.shift(1)

        long_mask = (stc > p["oversold"]) & (prev <= p["oversold"])
        short_mask = (stc < p["overbought"]) & (prev >= p["overbought"])

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        stc = df[self._col(p)]
        prev = stc.shift(1)
        crosses_into_overbought = (stc > p["overbought"]) & (prev <= p["overbought"])
        crosses_into_oversold = (stc < p["oversold"]) & (prev >= p["oversold"])
        return crosses_into_overbought | crosses_into_oversold
