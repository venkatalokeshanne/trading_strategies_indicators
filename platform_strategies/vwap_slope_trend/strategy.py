"""
VWAP Slope Trend.

The session VWAP's own slope over a short lookback, normalized by ATR
(so the "how steep counts as trending" threshold scales with the
instrument's own volatility rather than being a fixed price amount),
gates a simple regime read: bullish once the slope clears a minimum
threshold, bearish once it clears the threshold on the downside,
ranging in between.

Entry: fires on the bar the VWAP slope regime first turns bullish
(long) or bearish (short).
Exit: the next regime flip (to bearish while long, to bullish while
short, or briefly through the ranging middle).

This file contains ONLY strategy logic -- VWAP/ATR math lives in
app.indicators and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators._shared import true_range, wilders_smooth
from app.indicators.vwap import VWAP
from app.strategies.registry import strategy_registry


@strategy_registry.register("vwap_slope_trend")
class VWAPSlopeTrend(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="vwap_slope_trend",
            display_name="VWAP Slope Trend",
            description="ATR-normalized VWAP slope regime -- trades the flip into a bullish or bearish slope, exits on the next regime flip.",
            category="trend_following",
            indicators_used=["vwap", "atr"],
            default_params={"slope_lookback": 5, "min_slope": 0.03, "atr_period": 14, "direction": "both"},
            entry_conditions=[
                "Long: (VWAP - VWAP N bars ago) / ATR crosses above min_slope",
                "Short: the same normalized slope crosses below -min_slope",
            ],
            exit_conditions=["The next VWAP-slope regime flip"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = VWAP().calculate(df, {})
        out["vwap_slope_trend_atr"] = wilders_smooth(true_range(out), p["atr_period"])
        return out

    def _regimes(self, df: pd.DataFrame, p: dict[str, Any]) -> tuple[pd.Series, pd.Series]:
        vwap = df["vwap"]
        atr = df["vwap_slope_trend_atr"]
        slope = vwap - vwap.shift(p["slope_lookback"])
        normalized_slope = (slope / atr.replace(0, float("nan"))).fillna(0.0)

        bull_trend = normalized_slope > p["min_slope"]
        bear_trend = normalized_slope < -p["min_slope"]
        return bull_trend, bear_trend

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        bull_trend, bear_trend = self._regimes(df, p)
        bull_start = bull_trend & ~bull_trend.shift(1).fillna(False).infer_objects(copy=False).astype(bool)
        bear_start = bear_trend & ~bear_trend.shift(1).fillna(False).infer_objects(copy=False).astype(bool)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[bull_start] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[bear_start] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        bull_trend, bear_trend = self._regimes(df, p)
        bull_start = bull_trend & ~bull_trend.shift(1).fillna(False).infer_objects(copy=False).astype(bool)
        bear_start = bear_trend & ~bear_trend.shift(1).fillna(False).infer_objects(copy=False).astype(bool)
        return bull_start | bear_start
