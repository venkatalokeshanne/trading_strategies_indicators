"""
Fibonacci Retracement Bounce.

Trades the pullback: after a trailing N-bar swing, the 61.8%/50%
retracement zone is where a healthy pullback is expected to find
support (in an up-swing) or resistance (in a down-swing) before the
prior move resumes. Enters on the rejection out of that zone, targets
back toward the shallow 23.6% level near the swing extreme.

Entry: price dips into the 61.8% level and closes back above the 50%
level (long -- bounce off support), or pokes into the 61.8% level (read
from the down side) and closes back below the 50% level (short --
rejection at resistance).
Exit: price closes back through the shallow 23.6% level, in either
direction (profit-taking near the prior swing extreme).

This file contains ONLY strategy logic -- Fibonacci math lives in
app.indicators.fibonacci_retracement and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.fibonacci_retracement import FibonacciRetracement
from app.strategies.registry import strategy_registry


@strategy_registry.register("fib_retracement_bounce")
class FibRetracementBounce(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="fib_retracement_bounce",
            display_name="Fibonacci Retracement Bounce",
            description="Trades rejections out of the 61.8%/50% Fibonacci retracement zone of the trailing swing range.",
            category="mean_reversion",
            indicators_used=["fibonacci_retracement"],
            default_params={"period": 50, "direction": "both"},
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        return FibonacciRetracement().calculate(df, {"period": p["period"]})

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        level_618, level_50 = df["fib_retracement_618"], df["fib_retracement_5"]
        high, low, close = df["high"], df["low"], df["close"]

        long_mask = (low <= level_618) & (close > level_50)
        short_mask = (high >= level_618) & (close < level_50)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        level_236 = df["fib_retracement_236"]
        close, prev_close = df["close"], df["close"].shift(1)
        cross_up = (close >= level_236) & (prev_close < level_236)
        cross_down = (close <= level_236) & (prev_close > level_236)
        return cross_up | cross_down
