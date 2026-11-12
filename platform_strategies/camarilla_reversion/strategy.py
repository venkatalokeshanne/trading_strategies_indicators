"""
Camarilla Reversion.

A classic intraday mean-reversion play on Camarilla's tight R3/S3
levels: derived from the PRIOR session's range, they mark where price
is statistically likely to reject and revert back toward the middle
of the range rather than break through. Enters on the rejection,
targets the shallower R1/S1 band on the way back.

Entry: price pokes at/through R3 and closes back under it (short) or
pokes at/through S3 and closes back over it (long).
Exit: price reverts back inside the R1/S1 band.

This file contains ONLY strategy logic -- Camarilla math lives in
app.indicators.camarilla_pivots and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.camarilla_pivots import CamarillaPivots
from app.strategies.registry import strategy_registry


@strategy_registry.register("camarilla_reversion")
class CamarillaReversion(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="camarilla_reversion",
            display_name="Camarilla Reversion",
            description="Fades rejections at Camarilla's R3/S3 levels, targeting reversion back inside the R1/S1 band.",
            category="mean_reversion",
            indicators_used=["camarilla_pivots"],
            default_params={"direction": "both"},
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        self.validate_params(params)
        return CamarillaPivots().calculate(df, {})

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        r3, s3 = df["camarilla_r3"], df["camarilla_s3"]
        high, low, close = df["high"], df["low"], df["close"]

        short_mask = (high >= r3) & (close < r3)
        long_mask = (low <= s3) & (close > s3)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        r1, s1 = df["camarilla_r1"], df["camarilla_s1"]
        close = df["close"]
        return (close <= r1) & (close >= s1)
