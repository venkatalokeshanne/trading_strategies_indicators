"""
Order Block Retest.

Trades the ICT-style continuation read: once a bullish/bearish order
block has formed (the last opposing candle before a strong impulsive
move), a later pullback that retests the block's zone and holds is
read as smart-money re-accumulation, not a reversal -- price is
expected to resume the original impulsive direction.

Entry: price retraces back down into the most recent (still-fresh)
bullish order block zone and closes back above its top (long);
mirrored for a bearish order block (short).
Exit: price closes back through the far side of that same zone (the
retest failed and the level is invalidated).

This file contains ONLY strategy logic -- order block detection lives
in app.indicators.order_blocks and is reused as-is. The only thing
done here is forward-filling each block's zone forward in time (capped
at a max age) so later bars can "retest" a level the indicator only
flagged once, on the bar it formed.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.order_blocks import OrderBlocks
from app.strategies.registry import strategy_registry


@strategy_registry.register("order_block_retest")
class OrderBlockRetest(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="order_block_retest",
            display_name="Order Block Retest",
            description="Trades a pullback into the most recent bullish/bearish order block as smart-money re-accumulation, continuing the original impulsive move.",
            category="price_action",
            indicators_used=["order_blocks"],
            default_params={
                "atr_period": 14,
                "impulse_bars": 5,
                "impulse_atr_multiple": 2.0,
                "max_zone_age_bars": 100,
                "direction": "both",
            },
            live_caution=(
                "An order block only becomes valid once price has already displaced away from it, so "
                "the zone -- and any later retest of it -- is confirmed well after the fact; real fills "
                "will typically land later and worse than the backtest assumes."
            ),
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = OrderBlocks().calculate(
            df,
            {
                "atr_period": p["atr_period"],
                "impulse_bars": p["impulse_bars"],
                "impulse_atr_multiple": p["impulse_atr_multiple"],
            },
        )
        limit = p["max_zone_age_bars"]
        # Each zone is only flagged on its formation bar -- forward-fill
        # (capped at max_zone_age_bars) so later bars can test against
        # the most recent still-fresh zone instead of only its own bar.
        out["bullish_ob_top"] = out["bullish_ob_top"].ffill(limit=limit)
        out["bullish_ob_bottom"] = out["bullish_ob_bottom"].ffill(limit=limit)
        out["bearish_ob_top"] = out["bearish_ob_top"].ffill(limit=limit)
        out["bearish_ob_bottom"] = out["bearish_ob_bottom"].ffill(limit=limit)
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        bull_top, bull_bottom = df["bullish_ob_top"], df["bullish_ob_bottom"]
        bear_top, bear_bottom = df["bearish_ob_top"], df["bearish_ob_bottom"]
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
        bull_bottom, bear_top = df["bullish_ob_bottom"], df["bearish_ob_top"]
        close = df["close"]
        long_invalidated = close < bull_bottom
        short_invalidated = close > bear_top
        return long_invalidated | short_invalidated
