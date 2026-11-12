"""
Keltner Breakout Trend.

Long-only trend-following on a Keltner Channel: enters when close
breaks above the upper band (EMA + multiple x ATR) and stays in until
close falls back below the EMA midline -- a wide "enter fast, exit
slow" band pair designed to hold a trend through minor pullbacks
rather than exit on the first sign of weakness. The source script's
own defaults (EMA 160 / ATR 14 / 2.5x) were tuned for a 4h chart; kept
as-is here as the strategy's own defaults, tunable per params.

Entry: close closes above the upper Keltner band (EMA + atr_multiple x
ATR), only while flat.
Exit: close closes back below the Keltner midline (EMA).

This file contains ONLY strategy logic -- Keltner math lives in
app.indicators.keltner and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.keltner import KeltnerChannels
from app.strategies.registry import strategy_registry


@strategy_registry.register("keltner_breakout_trend")
class KeltnerBreakoutTrend(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="keltner_breakout_trend",
            display_name="Keltner Breakout Trend",
            description="Long-only: enters on a close above the upper Keltner band, exits on a close back below the EMA midline.",
            category="trend_following",
            indicators_used=["keltner"],
            default_params={"ema_period": 160, "atr_period": 14, "atr_multiple": 2.5},
            entry_conditions=["Close closes above the upper Keltner band (EMA + atr_multiple x ATR), only while flat"],
            exit_conditions=["Close closes back below the Keltner midline (EMA)"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        return KeltnerChannels().calculate(
            df, {"ema_period": p["ema_period"], "atr_period": p["atr_period"], "atr_multiple": p["atr_multiple"]}
        )

    def _cols(self, p: dict[str, Any]) -> tuple[str, str]:
        suffix = f"{p['ema_period']}_{p['atr_period']}"
        return f"keltner_middle_{suffix}", f"keltner_upper_{suffix}"

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        _, upper_col = self._cols(p)
        entries = pd.Series(None, index=df.index, dtype=object)
        entries[df["close"] > df[upper_col]] = TradeDirection.LONG
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        middle_col, _ = self._cols(p)
        return df["close"] < df[middle_col]
