"""
Chandelier Trend.

A stop-and-reverse trend system built directly on the Chandelier Exit
lines: staying long is valid while price holds above its long-side
trailing stop; a close through that stop is treated as the trend
flipping, and the mirror image on the short side.

Entry: close crosses above the short-side chandelier line (breakout
out of a downtrend -> flip long) or below the long-side chandelier
line (breakdown out of an uptrend -> flip short).
Exit: the same two crossings, applied direction-agnostically so
whichever side is open gets closed by its own stop line.

This file contains ONLY strategy logic -- Chandelier Exit math lives
in app.indicators.chandelier_exit and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.chandelier_exit import ChandelierExit
from app.strategies.registry import strategy_registry


@strategy_registry.register("chandelier_trend")
class ChandelierTrend(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="chandelier_trend",
            display_name="Chandelier Trend",
            description="Stop-and-reverse trend system: flips long/short whenever price closes through its Chandelier Exit trailing-stop line.",
            category="trend_following",
            indicators_used=["chandelier_exit"],
            default_params={"period": 22, "atr_multiple": 3.0, "direction": "both"},
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        return ChandelierExit().calculate(df, {"period": p["period"], "atr_multiple": p["atr_multiple"]})

    def _cols(self, p: dict[str, Any]) -> tuple[str, str]:
        n = p["period"]
        return f"chandelier_long_{n}", f"chandelier_short_{n}"

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        long_line_col, short_line_col = self._cols(p)
        long_line, short_line = df[long_line_col], df[short_line_col]
        close, prev_close = df["close"], df["close"].shift(1)

        cross_above_short_line = (close > short_line) & (prev_close <= short_line.shift(1))
        cross_below_long_line = (close < long_line) & (prev_close >= long_line.shift(1))

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[cross_above_short_line] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[cross_below_long_line] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        long_line_col, short_line_col = self._cols(p)
        long_line, short_line = df[long_line_col], df[short_line_col]
        close, prev_close = df["close"], df["close"].shift(1)

        cross_above_short_line = (close > short_line) & (prev_close <= short_line.shift(1))
        cross_below_long_line = (close < long_line) & (prev_close >= long_line.shift(1))
        return cross_above_short_line | cross_below_long_line
