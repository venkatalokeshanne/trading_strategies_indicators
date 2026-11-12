"""
EMA Cross RSI Filtered.

Long-only fast/slow EMA cross, filtered by RSI: only buy the bullish
cross while RSI is still below overbought (not chasing an already-hot
move), only close on the bearish cross while RSI is still above
oversold (not selling into an already-exhausted move). Distinct from
this platform's other EMA cross strategies (ema_cross reverses
position on every cross in either direction with no RSI filter;
sma_cross uses SMA and a fixed 3/8 pairing).

The source script also has a fixed-% stop-loss/take-profit -- not
ported here (risk management lives in this engine's own ExecutionConfig,
not hardcoded into strategies); pass execution.stop_loss_pct and
execution.take_profit_atr_multiple if you want a comparable overlay
(the source's take-profit is a flat %, this engine has no plain-%
take-profit field, only ATR-based).

Entry: fast EMA crosses above slow EMA AND RSI < overbought, only
while flat.
Exit: fast EMA crosses below slow EMA AND RSI > oversold.

This file contains ONLY strategy logic -- EMA/RSI math lives in
app.indicators and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.ema import EMA
from app.indicators.rsi import RSI
from app.strategies.registry import strategy_registry


@strategy_registry.register("ema_cross_rsi_filtered")
class EMACrossRSIFiltered(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="ema_cross_rsi_filtered",
            display_name="EMA Cross RSI Filtered",
            description="Long-only fast/slow EMA cross, filtered by RSI so entries don't chase an already-overbought move.",
            category="trend_following",
            indicators_used=["ema", "rsi"],
            default_params={
                "fast_period": 9,
                "slow_period": 21,
                "rsi_period": 14,
                "rsi_overbought": 70.0,
                "rsi_oversold": 30.0,
            },
            entry_conditions=["Fast EMA crosses above slow EMA AND RSI < rsi_overbought, only while flat"],
            exit_conditions=["Fast EMA crosses below slow EMA AND RSI > rsi_oversold"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = EMA().calculate(df, {"period": p["fast_period"], "source": "close"})
        out = EMA().calculate(out, {"period": p["slow_period"], "source": "close"})
        out = RSI().calculate(out, {"period": p["rsi_period"], "source": "close"})
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        fast, slow = df[f"ema_{p['fast_period']}"], df[f"ema_{p['slow_period']}"]
        rsi = df[f"rsi_{p['rsi_period']}"]
        prev_fast, prev_slow = fast.shift(1), slow.shift(1)

        cross_up = (fast > slow) & (prev_fast <= prev_slow)
        buy_signal = cross_up & (rsi < p["rsi_overbought"])

        entries = pd.Series(None, index=df.index, dtype=object)
        entries[buy_signal] = TradeDirection.LONG
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        fast, slow = df[f"ema_{p['fast_period']}"], df[f"ema_{p['slow_period']}"]
        rsi = df[f"rsi_{p['rsi_period']}"]
        prev_fast, prev_slow = fast.shift(1), slow.shift(1)

        cross_down = (fast < slow) & (prev_fast >= prev_slow)
        return cross_down & (rsi > p["rsi_oversold"])
