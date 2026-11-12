"""
Pivot Extended Reversion.

An evidence-based design, not a textbook default: backtesting this
platform's own Daily Levels feature across real tickers showed R1/S1
(and the equivalent Camarilla tier, already traded by
app.strategies.camarilla_reversion) get touched very often but hold as
support/resistance only ~45-55% of the time -- close to a coin flip,
since routine intraday range reaches them constantly. The EXTENDED
tier -- R2/R3 and S2/S3 -- gets touched far less often, but held
58-67% of the time in that same backtest: price rarely gets that far
without something real behind the move having already faded.

This strategy specifically skips R1/S1 and only fades the R2/R3 and
S2/S3 tier, targeting reversion back into the R1/S1 band.

Entry: price touches R2 or beyond (R2/R3) and closes back below R2
(short); touches S2 or beyond (S2/S3) and closes back above S2 (long).
Exit: price reverts back inside the R1/S1 band.

This file contains ONLY strategy logic -- Pivot Point math lives in
app.indicators.pivot_points and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.pivot_points import PivotPoints
from app.strategies.registry import strategy_registry


@strategy_registry.register("pivot_extended_reversion")
class PivotExtendedReversion(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="pivot_extended_reversion",
            display_name="Pivot Extended Reversion",
            description="Fades only the extended R2/R3 and S2/S3 pivot tier -- backtested as meaningfully more reliable than R1/S1 -- targeting reversion back into the R1/S1 band.",
            category="mean_reversion",
            indicators_used=["pivot_points"],
            default_params={"direction": "both"},
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        self.validate_params(params)
        return PivotPoints().calculate(df, {})

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        r2, s2 = df["pivot_r2"], df["pivot_s2"]
        high, low, close = df["high"], df["low"], df["close"]

        short_mask = (high >= r2) & (close < r2)
        long_mask = (low <= s2) & (close > s2)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        r1, s1 = df["pivot_r1"], df["pivot_s1"]
        close = df["close"]
        return (close <= r1) & (close >= s1)
