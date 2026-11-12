"""
Liquidity Sweep Reversal.

Trades the "stop hunt" pattern directly: a bullish sweep (price pokes
below a recent swing low, on resting sell-stops, then reclaims it same
bar) is read as a failed breakdown -- smart-money accumulation -- and
traded long. The mirror bearish sweep is traded short.

Entry: a bullish sweep (long) or bearish sweep (short) fires.
Exit: any new sweep event (either direction) -- the level being traded
has just been re-tested, so the original read is stale.

This file contains ONLY strategy logic -- sweep detection lives in
app.indicators.liquidity_sweep and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.liquidity_sweep import LiquiditySweep
from app.strategies.registry import strategy_registry


@strategy_registry.register("liquidity_sweep_reversal")
class LiquiditySweepReversal(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="liquidity_sweep_reversal",
            display_name="Liquidity Sweep Reversal",
            description="Trades the stop-hunt pattern: a swing low/high poked through then reclaimed same bar, read as a failed breakout.",
            category="price_action",
            indicators_used=["liquidity_sweep"],
            default_params={"swing_lookback": 20, "direction": "both"},
            live_caution=(
                "The setup requires catching a wick-through-and-reclaim within the SAME bar -- waiting "
                "for that bar to close (as a backtest silently does) means the reversal has already "
                "played out; real-time entries need intrabar reaction a periodic manual check can't give."
            ),
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        return LiquiditySweep().calculate(df, {"swing_lookback": p["swing_lookback"]})

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        bullish, bearish = df["liquidity_sweep_bullish"], df["liquidity_sweep_bearish"]

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[bullish] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[bearish] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        return df["liquidity_sweep_bullish"] | df["liquidity_sweep_bearish"]
