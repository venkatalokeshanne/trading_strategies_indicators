"""
CCI Signal Cross.

Trades CCI crossing its own SMA signal line -- a distinct read from
this platform's other CCI strategy (cci_extreme_reversal, which trades
the snap-back through the +/-100 band): this one reacts to CCI's own
momentum shifting relative to its recent average, not to a fixed
extreme level.

Entry: CCI crosses above (long) / below (short) its own signal-period
SMA.
Exit: the next crossover in the opposite direction.

This file contains ONLY strategy logic -- CCI math lives in
app.indicators.cci and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.cci import CCI
from app.strategies.registry import strategy_registry


@strategy_registry.register("cci_signal_cross")
class CCISignalCross(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="cci_signal_cross",
            display_name="CCI Signal Cross",
            description="Trades CCI crossing its own SMA signal line -- a momentum-shift read, distinct from the +/-100 extreme-reversal system.",
            category="mean_reversion",
            indicators_used=["cci"],
            default_params={"cci_period": 20, "signal_period": 9, "direction": "both"},
            entry_conditions=[
                "Long: CCI crosses above its own signal-period SMA",
                "Short: CCI crosses below its own signal-period SMA",
            ],
            exit_conditions=["The next CCI/signal crossover in the opposite direction"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = CCI().calculate(df, {"period": p["cci_period"]})
        out[f"cci_signal_{p['cci_period']}_{p['signal_period']}"] = (
            out[f"cci_{p['cci_period']}"].rolling(window=p["signal_period"], min_periods=p["signal_period"]).mean()
        )
        return out

    def _cols(self, p: dict[str, Any]) -> tuple[str, str]:
        return f"cci_{p['cci_period']}", f"cci_signal_{p['cci_period']}_{p['signal_period']}"

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        cci_col, signal_col = self._cols(p)
        cci, signal = df[cci_col], df[signal_col]
        prev_cci, prev_signal = cci.shift(1), signal.shift(1)

        cross_up = (cci > signal) & (prev_cci <= prev_signal)
        cross_down = (cci < signal) & (prev_cci >= prev_signal)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[cross_up] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[cross_down] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        cci_col, signal_col = self._cols(p)
        cci, signal = df[cci_col], df[signal_col]
        prev_cci, prev_signal = cci.shift(1), signal.shift(1)
        return ((cci > signal) != (prev_cci > prev_signal)) & prev_cci.notna() & prev_signal.notna()
