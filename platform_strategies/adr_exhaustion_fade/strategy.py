"""
ADR Exhaustion Fade.

Average Daily Range projects how far a stock typically moves in a
session, anchored to today's own open (the same "ADR expected range"
shown on the Daily Levels page). Once price has already reached that
projected high or low for the day, pushing further in the same
direction gets statistically less likely -- the day's typical move is
already spent. Trades a rejection at that boundary, targeting
reversion back to today's open.

Entry: price reaches/exceeds the ADR-projected high and closes back
under it (short); reaches/exceeds the ADR-projected low and closes
back above it (long).
Exit: price reverts back to today's session open.

This file contains ONLY strategy logic -- ADR math lives in
app.indicators.adr and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.adr import AverageDailyRange
from app.strategies.registry import strategy_registry


@strategy_registry.register("adr_exhaustion_fade")
class ADRExhaustionFade(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="adr_exhaustion_fade",
            display_name="ADR Exhaustion Fade",
            description="Fades a rejection once price reaches the Average-Daily-Range-projected high/low for the session, targeting reversion back to today's open.",
            category="mean_reversion",
            indicators_used=["adr"],
            default_params={"adr_period": 14, "direction": "both"},
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = AverageDailyRange().calculate(df, {"period": p["adr_period"]})
        session_date = pd.Series(out.index.date, index=out.index)
        out["session_open"] = out["open"].groupby(session_date).transform("first")
        adr_col = f"adr_{p['adr_period']}"
        out["adr_expected_high"] = out["session_open"] + out[adr_col]
        out["adr_expected_low"] = out["session_open"] - out[adr_col]
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        expected_high, expected_low = df["adr_expected_high"], df["adr_expected_low"]
        high, low, close = df["high"], df["low"], df["close"]

        short_mask = (high >= expected_high) & (close < expected_high)
        long_mask = (low <= expected_low) & (close > expected_low)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        session_open, close = df["session_open"], df["close"]
        prev_close, prev_open = close.shift(1), session_open.shift(1)
        return ((close > session_open) != (prev_close > prev_open)) & prev_open.notna()
