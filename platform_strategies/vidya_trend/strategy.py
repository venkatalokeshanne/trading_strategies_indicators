"""
VIDYA Trend.

VIDYA's smoothing speed already adapts to how choppy vs. trending the
market currently is (it slows down in chop, speeds up in trends), so a
plain price/VIDYA cross behaves like an adaptive-period EMA cross
without needing a separate regime filter.

Entry: close crosses above (long) / below (short) VIDYA.
Exit: the next crossover in the opposite direction.

This file contains ONLY strategy logic -- VIDYA math lives in
app.indicators.vidya and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.vidya import VIDYA
from app.strategies.registry import strategy_registry


@strategy_registry.register("vidya_trend")
class VIDYATrend(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="vidya_trend",
            display_name="VIDYA Trend",
            description="Price/VIDYA cross -- VIDYA's own smoothing speed already adapts to trending vs. choppy conditions.",
            category="trend_following",
            indicators_used=["vidya"],
            default_params={"period": 14, "cmo_period": 9, "direction": "both"},
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        return VIDYA().calculate(df, {"period": p["period"], "cmo_period": p["cmo_period"]})

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        vidya, close = df[f"vidya_{p['period']}"], df["close"]
        prev_vidya, prev_close = vidya.shift(1), close.shift(1)

        cross_up = (close > vidya) & (prev_close <= prev_vidya)
        cross_down = (close < vidya) & (prev_close >= prev_vidya)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[cross_up] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[cross_down] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        vidya, close = df[f"vidya_{p['period']}"], df["close"]
        prev_vidya, prev_close = vidya.shift(1), close.shift(1)
        return ((close > vidya) != (prev_close > prev_vidya)) & prev_vidya.notna()
