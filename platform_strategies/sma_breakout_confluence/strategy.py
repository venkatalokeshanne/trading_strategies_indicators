"""
SMA Breakout Confluence.

Long-only: close crossing above a short SMA is only traded when two
independent momentum reads both agree it's a real breakout, not a
whipsaw -- RSI already above its own midline (50) and MACD's line
already above its own signal line. Requiring all three at once is
stricter than any pair alone.

Entry: close crosses above SMA(ma_period) AND RSI > 50 AND MACD line
> MACD signal line, only while flat.
Exit: the triggering confluence breaks (any of the three conditions
turns false).

This file contains ONLY strategy logic -- SMA/RSI/MACD math lives in
app.indicators and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.macd import MACD
from app.indicators.rsi import RSI
from app.indicators.sma import SMA
from app.strategies.registry import strategy_registry


@strategy_registry.register("sma_breakout_confluence")
class SMABreakoutConfluence(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="sma_breakout_confluence",
            display_name="SMA Breakout Confluence",
            description="Long-only: close crosses above an SMA, confirmed by RSI above 50 and MACD line above its signal line.",
            category="trend_following",
            indicators_used=["sma", "rsi", "macd"],
            default_params={
                "ma_period": 10,
                "rsi_period": 14,
                "macd_fast_period": 12,
                "macd_slow_period": 26,
                "macd_signal_period": 9,
            },
            entry_conditions=["Close crosses above SMA(ma_period) AND RSI > 50 AND MACD line > MACD signal, only while flat"],
            exit_conditions=["The triggering confluence breaks (any of the three conditions turns false)"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = SMA().calculate(df, {"period": p["ma_period"], "source": "close"})
        out = RSI().calculate(out, {"period": p["rsi_period"], "source": "close"})
        out = MACD().calculate(
            out,
            {
                "fast_period": p["macd_fast_period"],
                "slow_period": p["macd_slow_period"],
                "signal_period": p["macd_signal_period"],
                "source": "close",
            },
        )
        return out

    def _macd_cols(self, p: dict[str, Any]) -> tuple[str, str]:
        suffix = f"{p['macd_fast_period']}_{p['macd_slow_period']}_{p['macd_signal_period']}"
        return f"macd_line_{suffix}", f"macd_signal_{suffix}"

    def _condition(self, df: pd.DataFrame, p: dict[str, Any]) -> pd.Series:
        sma = df[f"sma_{p['ma_period']}"]
        rsi = df[f"rsi_{p['rsi_period']}"]
        macd_col, signal_col = self._macd_cols(p)

        above_sma = df["close"] > sma
        rsi_bullish = rsi > 50
        macd_bullish = df[macd_col] > df[signal_col]
        return above_sma & rsi_bullish & macd_bullish

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        sma = df[f"sma_{p['ma_period']}"]
        prev_close, prev_sma = df["close"].shift(1), sma.shift(1)
        crossed_up = (df["close"] > sma) & (prev_close <= prev_sma)

        condition = self._condition(df, p)
        buy_signal = crossed_up & condition

        entries = pd.Series(None, index=df.index, dtype=object)
        entries[buy_signal] = TradeDirection.LONG
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        condition = self._condition(df, p)
        prev_condition = condition.shift(1).fillna(False).infer_objects(copy=False).astype(bool)
        return prev_condition & ~condition
