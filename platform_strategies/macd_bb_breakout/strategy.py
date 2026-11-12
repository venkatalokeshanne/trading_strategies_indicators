"""
MACD Bollinger Band Breakout.

Combines two independent confirmations before entering: a MACD
signal-line cross (momentum has turned) AND the close already
punching through a Bollinger Band (the move has enough force to break
its own recent volatility envelope). Requiring both at once is
stricter than either alone -- fewer signals, but each one has both a
momentum shift and a volatility breakout behind it.

Entry: MACD line crosses above its signal line with close above the
upper Bollinger Band (long); MACD line crosses below signal with close
below the lower Bollinger Band (short).
Exit: the next MACD signal-line cross in the opposite direction.

This file contains ONLY strategy logic -- MACD/Bollinger Band math
lives in app.indicators.macd / app.indicators.bbands and is reused
as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.bbands import BollingerBands
from app.indicators.macd import MACD
from app.strategies.registry import strategy_registry


@strategy_registry.register("macd_bb_breakout")
class MACDBBBreakout(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="macd_bb_breakout",
            display_name="MACD Bollinger Band Breakout",
            description="Trades a MACD signal-line cross only when it coincides with the close already breaking its own Bollinger Band.",
            category="breakout",
            indicators_used=["macd", "bbands"],
            default_params={
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9,
                "bb_period": 20,
                "bb_std_dev": 2.0,
                "direction": "both",
            },
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = MACD().calculate(
            df, {"fast_period": p["fast_period"], "slow_period": p["slow_period"], "signal_period": p["signal_period"]}
        )
        out = BollingerBands().calculate(out, {"period": p["bb_period"], "std_dev": p["bb_std_dev"]})
        return out

    def _macd_cols(self, p: dict[str, Any]) -> tuple[str, str]:
        suffix = f"{p['fast_period']}_{p['slow_period']}_{p['signal_period']}"
        return f"macd_line_{suffix}", f"macd_signal_{suffix}"

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        line_col, signal_col = self._macd_cols(p)
        macd_line, signal_line = df[line_col], df[signal_col]
        prev_line, prev_signal = macd_line.shift(1), signal_line.shift(1)
        upper, lower = df[f"bbands_upper_{p['bb_period']}"], df[f"bbands_lower_{p['bb_period']}"]
        close = df["close"]

        cross_up = (macd_line > signal_line) & (prev_line <= prev_signal) & (close > upper)
        cross_down = (macd_line < signal_line) & (prev_line >= prev_signal) & (close < lower)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[cross_up] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[cross_down] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        line_col, signal_col = self._macd_cols(p)
        macd_line, signal_line = df[line_col], df[signal_col]
        prev_line, prev_signal = macd_line.shift(1), signal_line.shift(1)
        return ((macd_line > signal_line) != (prev_line > prev_signal)) & prev_line.notna() & prev_signal.notna()
