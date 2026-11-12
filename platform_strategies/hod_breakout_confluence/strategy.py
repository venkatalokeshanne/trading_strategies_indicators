"""
HOD Breakout Confluence.

A five-way long-only confluence near the current session's high: RSI
strength, a volume surge vs its own average, price above both VWAP and
a short EMA, and close sitting within a buffer of the running
session-high-so-far. All five must agree on the same bar.

The source script hardcodes a specific intraday clock window (15:15-
15:25 IST) as part of the signal itself -- not ported here; this
platform's own execution.entry_window_start/end (ExecutionConfig)
already provides that same "only take entries in a clock window" gate
uniformly for every strategy, so use it instead of baking a fixed
window into this strategy's logic.

Entry: close within hod_buffer_pct of the running session high, AND
volume > vol_multiplier * its own average, AND close > VWAP, AND
close > EMA(ema_period), AND RSI(rsi_period) >= rsi_threshold.
Exit: any one of the five conditions stops holding.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.ema import EMA
from app.indicators.period_high_low import PeriodHighLow
from app.indicators.rsi import RSI
from app.indicators.volume_average import VolumeAverage
from app.indicators.vwap import VWAP
from app.strategies.registry import strategy_registry


@strategy_registry.register("hod_breakout_confluence")
class HODBreakoutConfluence(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="hod_breakout_confluence",
            display_name="HOD Breakout Confluence",
            description="Long-only: close near the running session high, confirmed by a volume surge, VWAP/EMA position, and RSI strength, all at once.",
            category="momentum",
            indicators_used=["rsi", "vwap", "ema", "volume_average", "period_high_low"],
            default_params={
                "rsi_period": 14,
                "rsi_threshold": 60.0,
                "ema_period": 20,
                "volume_avg_period": 20,
                "volume_multiplier": 1.5,
                "hod_buffer_pct": 0.8,
                "direction": "long_only",
            },
            entry_conditions=[
                "close within hod_buffer_pct% of the running session high",
                "volume > volume_multiplier * its own average",
                "close > VWAP and close > EMA(ema_period)",
                "RSI(rsi_period) >= rsi_threshold",
            ],
            exit_conditions=["Any one of the five entry conditions stops holding"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = RSI().calculate(df, {"period": p["rsi_period"], "source": "close"})
        out = VWAP().calculate(out, {})
        out = EMA().calculate(out, {"period": p["ema_period"], "source": "close"})
        out = VolumeAverage().calculate(out, {"period": p["volume_avg_period"]})
        out = PeriodHighLow().calculate(out, {"period": "D"})
        return out

    def _confluence(self, df: pd.DataFrame, p: dict[str, Any]) -> pd.Series:
        near_hod = df["close"] >= df["period_high_D"] * (1 - p["hod_buffer_pct"] / 100)
        vol_spike = df["volume"] > df[f"volume_avg_{p['volume_avg_period']}"] * p["volume_multiplier"]
        above_vwap = df["close"] > df["vwap"]
        above_ema = df["close"] > df[f"ema_{p['ema_period']}"]
        rsi_ok = df[f"rsi_{p['rsi_period']}"] >= p["rsi_threshold"]
        return near_hod & vol_spike & above_vwap & above_ema & rsi_ok

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        entries = pd.Series(None, index=df.index, dtype=object)
        entries[self._confluence(df, p)] = TradeDirection.LONG
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        return ~self._confluence(df, p)
