"""
Multi-EMA Alignment Cross.

A fast/medium EMA cross (20/50), but only taken while a full 4-EMA
stack (20/50/100/200) already agrees on direction -- the medium EMA
must sit above the slow EMA which must sit above the baseline EMA for
a long entry (fully reversed for a short). Distinct from this
platform's other EMA cross strategies: ema_cross has no stack-alignment
gate at all; ema_convergence_trend gates on 2 EMAs converging, not a
4-EMA hierarchy.

Entry: EMA(20) crosses above EMA(50) AND EMA(50) > EMA(100) > EMA(200)
(long); mirrored for short.
Exit: the opposite-direction cross+alignment signal.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.ema import EMA
from app.strategies.registry import strategy_registry


@strategy_registry.register("multi_ema_alignment_cross")
class MultiEMAAlignmentCross(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="multi_ema_alignment_cross",
            display_name="Multi-EMA Alignment Cross",
            description="Trades a fast/medium EMA cross only while a full 4-EMA stack (20/50/100/200) already agrees on direction.",
            category="trend_following",
            indicators_used=["ema"],
            default_params={
                "fast_period": 20,
                "medium_period": 50,
                "slow_period": 100,
                "baseline_period": 200,
                "direction": "both",
            },
            entry_conditions=[
                "Long: EMA(fast) crosses above EMA(medium) AND EMA(medium) > EMA(slow) > EMA(baseline)",
                "Short: EMA(fast) crosses below EMA(medium) AND EMA(medium) < EMA(slow) < EMA(baseline)",
            ],
            exit_conditions=["The opposite-direction cross+alignment signal"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = EMA().calculate(df, {"period": p["fast_period"], "source": "close"})
        out = EMA().calculate(out, {"period": p["medium_period"], "source": "close"})
        out = EMA().calculate(out, {"period": p["slow_period"], "source": "close"})
        out = EMA().calculate(out, {"period": p["baseline_period"], "source": "close"})
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        fast = df[f"ema_{p['fast_period']}"]
        medium = df[f"ema_{p['medium_period']}"]
        slow = df[f"ema_{p['slow_period']}"]
        baseline = df[f"ema_{p['baseline_period']}"]
        prev_fast, prev_medium = fast.shift(1), medium.shift(1)

        cross_up = (fast > medium) & (prev_fast <= prev_medium)
        cross_down = (fast < medium) & (prev_fast >= prev_medium)
        bullish_alignment = (medium > slow) & (slow > baseline)
        bearish_alignment = (medium < slow) & (slow < baseline)

        long_mask = cross_up & bullish_alignment
        short_mask = cross_down & bearish_alignment

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        fast = df[f"ema_{p['fast_period']}"]
        medium = df[f"ema_{p['medium_period']}"]
        slow = df[f"ema_{p['slow_period']}"]
        baseline = df[f"ema_{p['baseline_period']}"]
        prev_fast, prev_medium = fast.shift(1), medium.shift(1)

        cross_up = (fast > medium) & (prev_fast <= prev_medium)
        cross_down = (fast < medium) & (prev_fast >= prev_medium)
        bullish_alignment = (medium > slow) & (slow > baseline)
        bearish_alignment = (medium < slow) & (slow < baseline)

        return (cross_up & bullish_alignment) | (cross_down & bearish_alignment)
