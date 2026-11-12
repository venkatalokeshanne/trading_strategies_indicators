"""
EMA Cross.

The classic fast/slow EMA cross (9/26 by default) -- reverses position
on every crossover rather than just flattening, so it's always long or
short, never flat, once past warmup.

The source script's stop-loss/take-profit are fixed POINT distances
(e.g. 20/40 points) anchored to the position's average entry price --
this engine's risk-management vocabulary (stop_loss_pct,
stop_loss_atr_multiple, take_profit_atr_multiple, ...) has no raw
fixed-point-distance equivalent, so it isn't ported here. Pass
execution.stop_loss_pct / take_profit_atr_multiple when running this
strategy if you want a comparable (percentage- or volatility-based,
not point-based) risk overlay.

Entry: fast EMA crosses above (long) / below (short) slow EMA --
always in the market once past warmup, since a cross in either
direction both closes the opposite side and opens the new one.
Exit: the next crossover in the opposite direction.

This file contains ONLY strategy logic -- EMA math lives in
app.indicators.ema and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.ema import EMA
from app.strategies.registry import strategy_registry


@strategy_registry.register("ema_cross")
class EMACross(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="ema_cross",
            display_name="EMA Cross",
            description="Classic fast/slow EMA cross (9/26 default) -- reverses position on every crossover, always long or short.",
            category="trend_following",
            indicators_used=["ema"],
            default_params={"fast_period": 9, "slow_period": 26, "direction": "both"},
            entry_conditions=[
                "Long: fast EMA crosses above slow EMA",
                "Short: fast EMA crosses below slow EMA",
            ],
            exit_conditions=["The next EMA crossover in the opposite direction"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = EMA().calculate(df, {"period": p["fast_period"], "source": "close"})
        out = EMA().calculate(out, {"period": p["slow_period"], "source": "close"})
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        fast, slow = df[f"ema_{p['fast_period']}"], df[f"ema_{p['slow_period']}"]
        prev_fast, prev_slow = fast.shift(1), slow.shift(1)

        cross_up = (fast > slow) & (prev_fast <= prev_slow)
        cross_down = (fast < slow) & (prev_fast >= prev_slow)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[cross_up] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[cross_down] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        fast, slow = df[f"ema_{p['fast_period']}"], df[f"ema_{p['slow_period']}"]
        prev_fast, prev_slow = fast.shift(1), slow.shift(1)
        return ((fast > slow) != (prev_fast > prev_slow)) & prev_fast.notna() & prev_slow.notna()
