"""
RSI Signal Cross.

Trades RSI crossing its own SMA signal line, gated by absolute RSI
level filters (default: only buy while RSI is still below 45, only
sell while RSI is still above 65 -- i.e. the cross has to happen away
from the opposite extreme, not right after leaving it) and an optional
"price above its own EMA" filter on the long side, to avoid buying a
signal-line cross during a still-falling price ("catching a falling
knife").

A distinct read from this platform's other RSI strategies: rsi_reversal
trades RSI touching a fixed 30/70 extreme directly, while this one
trades RSI's own momentum shifting relative to its recent average,
filtered by where RSI currently sits (and optionally, by trend).

Entry: RSI crosses above its own signal-period SMA AND RSI is still
below buy_max_rsi (long, optionally also requiring close > its own
trend EMA); RSI crosses below its own signal-period SMA AND RSI is
still above sell_min_rsi (short).
Exit: the next RSI/signal crossover in the opposite direction.

This file contains ONLY strategy logic -- RSI/EMA math lives in
app.indicators and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.ema import EMA
from app.indicators.rsi import RSI
from app.strategies.registry import strategy_registry


@strategy_registry.register("rsi_signal_cross")
class RSISignalCross(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="rsi_signal_cross",
            display_name="RSI Signal Cross",
            description="Trades RSI crossing its own SMA signal line, filtered by absolute RSI level (and optionally trend) so crosses right after an extreme don't qualify.",
            category="mean_reversion",
            indicators_used=["rsi", "ema"],
            default_params={
                "rsi_period": 14,
                "signal_period": 14,
                "buy_max_rsi": 45.0,
                "sell_min_rsi": 65.0,
                "use_trend_filter": False,
                "trend_ema_period": 9,
                "direction": "both",
            },
            entry_conditions=[
                "Long: RSI crosses above its own signal SMA AND RSI < buy_max_rsi (optionally also close > trend EMA)",
                "Short: RSI crosses below its own signal SMA AND RSI > sell_min_rsi",
            ],
            exit_conditions=["The next RSI/signal crossover in the opposite direction"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = RSI().calculate(df, {"period": p["rsi_period"], "source": "close"})
        out[f"rsi_signal_{p['rsi_period']}_{p['signal_period']}"] = (
            out[f"rsi_{p['rsi_period']}"].rolling(window=p["signal_period"], min_periods=p["signal_period"]).mean()
        )
        if p["use_trend_filter"]:
            out = EMA().calculate(out, {"period": p["trend_ema_period"], "source": "close"})
        return out

    def _cols(self, p: dict[str, Any]) -> tuple[str, str]:
        return f"rsi_{p['rsi_period']}", f"rsi_signal_{p['rsi_period']}_{p['signal_period']}"

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        rsi_col, signal_col = self._cols(p)
        rsi, signal = df[rsi_col], df[signal_col]
        prev_rsi, prev_signal = rsi.shift(1), signal.shift(1)

        cross_up = (rsi > signal) & (prev_rsi <= prev_signal)
        cross_down = (rsi < signal) & (prev_rsi >= prev_signal)

        buy_signal = cross_up & (rsi < p["buy_max_rsi"])
        if p["use_trend_filter"]:
            buy_signal = buy_signal & (df["close"] > df[f"ema_{p['trend_ema_period']}"])
        sell_signal = cross_down & (rsi > p["sell_min_rsi"])

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[buy_signal] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[sell_signal] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        rsi_col, signal_col = self._cols(p)
        rsi, signal = df[rsi_col], df[signal_col]
        prev_rsi, prev_signal = rsi.shift(1), signal.shift(1)
        return ((rsi > signal) != (prev_rsi > prev_signal)) & prev_rsi.notna() & prev_signal.notna()
