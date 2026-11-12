"""
QQE Trend.

QQE's smoothed RSI crossing its own midline (50) marks a momentum
regime flip; the width of QQE's volatility-adaptive band around that
line is used as a strength filter so only flips backed by expanding
momentum volatility (a genuine trend push, not noise) are taken.

Entry: smoothed RSI crosses above 50 (long) / below 50 (short), with
the QQE band wider than its own recent average at that moment.
Exit: smoothed RSI crosses back through 50.

This file contains ONLY strategy logic -- QQE math lives in
app.indicators.qqe and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.qqe import QQE
from app.strategies.registry import strategy_registry


@strategy_registry.register("qqe_trend")
class QQETrend(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="qqe_trend",
            display_name="QQE Trend",
            description="Trades QQE's smoothed-RSI midline flips, filtered to only the ones backed by expanding momentum volatility.",
            category="momentum",
            indicators_used=["qqe"],
            default_params={
                "rsi_period": 14,
                "smoothing_period": 5,
                "factor": 4.236,
                "band_strength_period": 20,
                "direction": "both",
            },
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        return QQE().calculate(
            df,
            {"rsi_period": p["rsi_period"], "smoothing_period": p["smoothing_period"], "factor": p["factor"]},
        )

    def _cols(self, p: dict[str, Any]) -> tuple[str, str, str]:
        suffix = f"{p['rsi_period']}_{p['smoothing_period']}"
        return f"qqe_rsi_{suffix}", f"qqe_upper_{suffix}", f"qqe_lower_{suffix}"

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        rsi_col, upper_col, lower_col = self._cols(p)
        rsi, upper, lower = df[rsi_col], df[upper_col], df[lower_col]
        prev_rsi = rsi.shift(1)

        band_width = upper - lower
        band_expanding = band_width > band_width.rolling(window=p["band_strength_period"]).mean()

        cross_up = (rsi > 50) & (prev_rsi <= 50) & band_expanding
        cross_down = (rsi < 50) & (prev_rsi >= 50) & band_expanding

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[cross_up] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[cross_down] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        rsi_col, _, _ = self._cols(p)
        rsi = df[rsi_col]
        prev_rsi = rsi.shift(1)
        return ((rsi > 50) != (prev_rsi > 50)) & prev_rsi.notna()
