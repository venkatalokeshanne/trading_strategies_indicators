"""
BB EMA Gap Reversion.

A mean-reversion read that uses the EMA's position WITHIN the
Bollinger Band as a directional tiebreaker: touching the lower band is
only traded if the EMA sits closer to the upper band (more room
below the EMA than above it, i.e. the band is skewed against the
touch) -- read as more room to revert upward. Touching the upper band
mirrors this on the downside.

Entry: Long when low touches/crosses the lower Bollinger Band AND the
gap from EMA to the lower band exceeds the gap from EMA to the upper
band. Short is the mirror image on the upper band.
Exit: the next opposite-direction signal.

This file contains ONLY strategy logic -- EMA/Bollinger Band math
lives in app.indicators and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.bbands import BollingerBands
from app.indicators.ema import EMA
from app.strategies.registry import strategy_registry


@strategy_registry.register("bb_ema_gap_reversion")
class BBEMAGapReversion(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="bb_ema_gap_reversion",
            display_name="BB EMA Gap Reversion",
            description="Touches the lower/upper Bollinger Band, traded only when the EMA sits skewed toward the opposite band (more room to revert).",
            category="mean_reversion",
            indicators_used=["ema", "bbands"],
            default_params={"ema_period": 9, "bb_period": 20, "bb_std_dev": 2.0, "direction": "both"},
            entry_conditions=[
                "Long: low touches/crosses the lower Bollinger Band AND (EMA-to-lower gap) > (EMA-to-upper gap)",
                "Short: high touches/crosses the upper Bollinger Band AND (EMA-to-upper gap) > (EMA-to-lower gap)",
            ],
            exit_conditions=["The next opposite-direction signal"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = EMA().calculate(df, {"period": p["ema_period"], "source": "close"})
        out = BollingerBands().calculate(out, {"period": p["bb_period"], "std_dev": p["bb_std_dev"], "source": "close"})
        return out

    def _signals(self, df: pd.DataFrame, p: dict[str, Any]) -> tuple[pd.Series, pd.Series]:
        ema = df[f"ema_{p['ema_period']}"]
        upper, lower = df[f"bbands_upper_{p['bb_period']}"], df[f"bbands_lower_{p['bb_period']}"]

        gap_to_upper = upper - ema
        gap_to_lower = ema - lower

        touched_lower = df["low"] <= lower
        touched_upper = df["high"] >= upper

        buy_signal = (gap_to_lower > gap_to_upper) & touched_lower
        sell_signal = (gap_to_upper > gap_to_lower) & touched_upper
        return buy_signal, sell_signal

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        buy_signal, sell_signal = self._signals(df, p)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[buy_signal] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[sell_signal] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        buy_signal, sell_signal = self._signals(df, p)
        return buy_signal | sell_signal
