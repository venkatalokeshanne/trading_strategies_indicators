"""
RSI Reversal.

The oldest, most mechanical RSI system there is: buy the instant RSI
touches oversold, sell the instant it touches overbought. Unlike the
other RSI-family strategies in this library (which wait for RSI to
bounce back OUT of the extreme first), this one buys the extreme
itself -- more aggressive, earlier, and more exposed to RSI staying
pinned at an extreme through a strong move.

Entry: RSI crosses down through the oversold threshold (long); RSI
crosses up through the overbought threshold (short).
Exit: RSI reaches the opposite threshold.

This file contains ONLY strategy logic -- RSI math lives in
app.indicators.rsi and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.rsi import RSI
from app.strategies.registry import strategy_registry


@strategy_registry.register("rsi_reversal")
class RSIReversal(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="rsi_reversal",
            display_name="RSI Reversal",
            description="Buys the instant RSI touches oversold and sells the instant it touches overbought -- the classic mechanical RSI system.",
            category="mean_reversion",
            indicators_used=["rsi"],
            default_params={"period": 14, "oversold": 30.0, "overbought": 70.0, "direction": "both"},
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        return RSI().calculate(df, {"period": p["period"]})

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        rsi = df[f"rsi_{p['period']}"]
        prev_rsi = rsi.shift(1)

        long_mask = (rsi <= p["oversold"]) & (prev_rsi > p["oversold"])
        short_mask = (rsi >= p["overbought"]) & (prev_rsi < p["overbought"])

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        rsi = df[f"rsi_{p['period']}"]
        prev_rsi = rsi.shift(1)
        reaches_overbought = (rsi >= p["overbought"]) & (prev_rsi < p["overbought"])
        reaches_oversold = (rsi <= p["oversold"]) & (prev_rsi > p["oversold"])
        return reaches_overbought | reaches_oversold
