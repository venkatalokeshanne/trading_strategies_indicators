"""
MACD Zone Crossover.

A MACD signal-line cross only counts if it happens on the "right side"
of the zero line: a bullish cross while MACD is already positive
(momentum turning up further into strength), or a bearish cross while
MACD is already negative (momentum turning down further into
weakness) -- filters out crosses that happen while momentum is still
fighting its way through zero.

The source script also splits signals into "volume-supported" vs
"regular" as a LABEL only (both still fire) -- ported here as an
optional stricter GATE instead (require_volume_support=True demands
above-average volume on the signal bar itself, off by default to match
the source's default behavior of firing on either).

Entry: MACD line crosses above its signal line while MACD > 0 (long);
crosses below while MACD < 0 (short).
Exit: the next opposite-direction zone crossover.

This file contains ONLY strategy logic -- MACD/volume math lives in
app.indicators and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.macd import MACD
from app.indicators.volume_average import VolumeAverage
from app.strategies.registry import strategy_registry


@strategy_registry.register("macd_zone_crossover")
class MACDZoneCrossover(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="macd_zone_crossover",
            display_name="MACD Zone Crossover",
            description="MACD signal-line cross, only while MACD is already on the matching side of zero (bullish cross above 0, bearish cross below 0).",
            category="momentum",
            indicators_used=["macd", "volume_average"],
            default_params={
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9,
                "require_volume_support": False,
                "volume_avg_period": 20,
                "direction": "both",
            },
            entry_conditions=[
                "Long: MACD line crosses above its signal line AND MACD line > 0 (optionally also volume > its own average)",
                "Short: MACD line crosses below its signal line AND MACD line < 0 (optionally also volume > its own average)",
            ],
            exit_conditions=["The next opposite-direction zone crossover"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = MACD().calculate(
            df, {"fast_period": p["fast_period"], "slow_period": p["slow_period"], "signal_period": p["signal_period"], "source": "close"}
        )
        if p["require_volume_support"]:
            out = VolumeAverage().calculate(out, {"period": p["volume_avg_period"]})
        return out

    def _cols(self, p: dict[str, Any]) -> tuple[str, str]:
        suffix = f"{p['fast_period']}_{p['slow_period']}_{p['signal_period']}"
        return f"macd_line_{suffix}", f"macd_signal_{suffix}"

    def _signals(self, df: pd.DataFrame, p: dict[str, Any]) -> tuple[pd.Series, pd.Series]:
        macd_col, signal_col = self._cols(p)
        macd_line, signal_line = df[macd_col], df[signal_col]
        prev_macd, prev_signal = macd_line.shift(1), signal_line.shift(1)

        cross_up = (macd_line > signal_line) & (prev_macd <= prev_signal)
        cross_down = (macd_line < signal_line) & (prev_macd >= prev_signal)

        buy_signal = cross_up & (macd_line > 0)
        sell_signal = cross_down & (macd_line < 0)

        if p["require_volume_support"]:
            volume_supporting = df["volume"] > df[f"volume_avg_{p['volume_avg_period']}"]
            buy_signal = buy_signal & volume_supporting
            sell_signal = sell_signal & volume_supporting
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
