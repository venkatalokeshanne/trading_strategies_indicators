"""
FVG Fill Continuation.

Trades the ICT-style "fill and go" read on Fair Value Gaps: a 3-bar
imbalance left by an impulsive move is read as an area price is likely
to revisit briefly before continuing -- so a retrace into a still-fresh
gap that then closes back through its far edge is traded as a
continuation of the original impulsive direction, not a reversal.

Entry: price retraces into the most recent (still-fresh) bullish FVG
zone and closes back above its top (long); mirrored for a bearish FVG
(short).
Exit: price closes back through the far side of that same gap (the
continuation failed).

This file contains ONLY strategy logic -- FVG detection lives in
app.indicators.fair_value_gap and is reused as-is. The only thing done
here is forward-filling each gap's zone forward in time (capped at a
max age) so later bars can "fill" a gap the indicator only flagged
once, on the bar it confirmed.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.fair_value_gap import FairValueGap
from app.strategies.registry import strategy_registry


@strategy_registry.register("fvg_fill_continuation")
class FVGFillContinuation(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="fvg_fill_continuation",
            display_name="FVG Fill Continuation",
            description="Trades a retrace into a still-fresh Fair Value Gap as a pause before the original impulsive move continues.",
            category="price_action",
            indicators_used=["fair_value_gap"],
            default_params={"max_zone_age_bars": 50, "direction": "both"},
            live_caution=(
                "Trading a retrace into the gap needs a fill at a specific, often narrow price zone -- "
                "a backtest assumes a clean fill the instant price crosses it, but that's a real "
                "slippage/no-fill risk live that the backtested numbers don't account for."
            ),
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = FairValueGap().calculate(df, {})
        limit = p["max_zone_age_bars"]
        out["fvg_bullish_top"] = out["fvg_bullish_top"].ffill(limit=limit)
        out["fvg_bullish_bottom"] = out["fvg_bullish_bottom"].ffill(limit=limit)
        out["fvg_bearish_top"] = out["fvg_bearish_top"].ffill(limit=limit)
        out["fvg_bearish_bottom"] = out["fvg_bearish_bottom"].ffill(limit=limit)
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        bull_top, bull_bottom = df["fvg_bullish_top"], df["fvg_bullish_bottom"]
        bear_top, bear_bottom = df["fvg_bearish_top"], df["fvg_bearish_bottom"]
        low, high, close = df["low"], df["high"], df["close"]

        long_mask = (low <= bull_top) & (low >= bull_bottom) & (close > bull_top)
        short_mask = (high >= bear_bottom) & (high <= bear_top) & (close < bear_bottom)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        bull_bottom, bear_top = df["fvg_bullish_bottom"], df["fvg_bearish_top"]
        close = df["close"]
        long_invalidated = close < bull_bottom
        short_invalidated = close > bear_top
        return long_invalidated | short_invalidated
