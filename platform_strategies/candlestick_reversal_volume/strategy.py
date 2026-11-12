"""
Candlestick Reversal + Volume.

Trades classic candlestick reversal patterns (hammer, shooting star,
engulfing, trend-context doji), but only when backed by an unusually
large burst of relative volume -- the same pattern on a quiet, thin
bar is far weaker evidence than one printed on 2x+ normal
participation.

Entry: a bullish reversal candle forms with relative volume above
threshold (long); a bearish reversal candle forms with relative volume
above threshold (short).
Exit: the opposite reversal pattern fires.

This file contains ONLY strategy logic -- pattern/volume math lives in
app.indicators.candlestick_reversal / app.indicators.rvol and is reused
as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.candlestick_reversal import CandlestickReversal
from app.indicators.rvol import RelativeVolume
from app.strategies.registry import strategy_registry


@strategy_registry.register("candlestick_reversal_volume")
class CandlestickReversalVolume(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="candlestick_reversal_volume",
            display_name="Candlestick Reversal + Volume",
            description="Trades hammer/shooting-star/engulfing/doji reversal patterns, only when confirmed by a 2x+ relative-volume burst.",
            category="price_action",
            indicators_used=["candlestick_reversal", "rvol"],
            default_params={
                "wick_body_ratio": 2.0,
                "doji_body_ratio": 0.1,
                "trend_lookback": 5,
                "rvol_period": 20,
                "rvol_threshold": 2.0,
                "direction": "both",
            },
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = CandlestickReversal().calculate(
            df,
            {
                "wick_body_ratio": p["wick_body_ratio"],
                "doji_body_ratio": p["doji_body_ratio"],
                "trend_lookback": p["trend_lookback"],
            },
        )
        out = RelativeVolume().calculate(out, {"period": p["rvol_period"]})
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        bullish, bearish = df["bullish_reversal_candle"], df["bearish_reversal_candle"]
        rvol = df[f"rvol_{p['rvol_period']}"]
        volume_confirmed = rvol > p["rvol_threshold"]

        long_mask = bullish & volume_confirmed
        short_mask = bearish & volume_confirmed

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        return df["bullish_reversal_candle"] | df["bearish_reversal_candle"]
