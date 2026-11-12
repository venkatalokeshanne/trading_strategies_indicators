"""
Morning EMA/VWAP Cross.

A morning-only momentum play: the EMA(9)/EMA(21) crossover is the
trigger, session VWAP is the confirmation that price sits on the right
side of the day's fair value, and the clock does the rest — signals
are only taken before a midday cutoff (mornings are when the crossover
carries follow-through), and anything still open late in the day is
closed so nothing is ever held overnight.

Entry: EMA(fast) crosses above EMA(slow) on this bar (was at/below on
the prior bar) AND the bar closes above session VWAP AND the bar's
time is before entry_cutoff (long); mirrored below VWAP for a short.
Exit: time only — the close of the first bar at or after flat_time
(the 15:45 bar on 5-minute data closes at 3:50 PM). There is
deliberately NO opposite-cross exit: this strategy is designed to run
with a hard ATR stop, an ATR take-profit, and risk-per-trade sizing,
which live in Execution Settings so they're enforced identically for
every strategy (e.g. 1.0x ATR(14) stop, 1.5x ATR take-profit, risk %
per trade with position value capped at 100% of capital).

This file contains ONLY strategy logic — EMA and VWAP math live in
app.indicators.ema / app.indicators.vwap and are reused as-is.
"""

from datetime import time, datetime
from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.ema import EMA
from app.indicators.vwap import VWAP
from app.strategies.registry import strategy_registry


def _parse_time(value: str) -> time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Expected a time in 'HH:MM' 24h format, got {value!r}.") from exc


@strategy_registry.register("ema_vwap_morning_cross")
class EMAVWAPMorningCross(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="ema_vwap_morning_cross",
            display_name="Morning EMA/VWAP Cross",
            description=(
                "Morning-only EMA(9)/EMA(21) crossover confirmed by which side of session VWAP "
                "the bar closes on; no entries after the midday cutoff and everything is flat by "
                "the flat_time bar's close. Designed to run with an ATR stop, ATR take-profit and "
                "risk-per-trade sizing from Execution Settings."
            ),
            category="trend_following",
            indicators_used=["ema", "vwap"],
            default_params={
                "fast_period": 9,
                "slow_period": 21,
                "entry_cutoff": "12:00",
                "flat_time": "15:45",
                "direction": "both",
            },
            entry_conditions=[
                "Long: EMA(fast) crosses above EMA(slow) on this bar (was at/below on the prior bar)",
                "Long: the bar closes above session VWAP",
                "Short: EMA(fast) crosses below EMA(slow) and the bar closes below session VWAP",
                "The bar's time is before entry_cutoff (no afternoon entries)",
            ],
            exit_conditions=[
                "Close of the first bar at or after flat_time (15:45 on 5-min data = flat by 3:50 PM)",
                "Stop-loss / take-profit come from Execution Settings (intended: 1.0x ATR stop, 1.5x ATR target)",
            ],
        )

    def validate_params(self, params: dict[str, Any]) -> dict[str, Any]:
        p = super().validate_params(params)
        if p["fast_period"] >= p["slow_period"]:
            raise ValueError(
                f"fast_period must be < slow_period (got {p['fast_period']} >= {p['slow_period']})."
            )
        _parse_time(p["entry_cutoff"])
        _parse_time(p["flat_time"])
        return p

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = EMA().calculate(df, {"period": p["fast_period"]})
        out = EMA().calculate(out, {"period": p["slow_period"]})
        return VWAP().calculate(out, {})

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        fast = df[f"ema_{p['fast_period']}"]
        slow = df[f"ema_{p['slow_period']}"]
        prev_fast, prev_slow = fast.shift(1), slow.shift(1)
        close, vwap = df["close"], df["vwap"]

        cutoff = _parse_time(p["entry_cutoff"])
        morning = pd.Series(df.index.time < cutoff, index=df.index)

        valid = prev_fast.notna() & prev_slow.notna()
        crossed_up = valid & (fast > slow) & (prev_fast <= prev_slow)
        crossed_down = valid & (fast < slow) & (prev_fast >= prev_slow)

        long_mask = morning & crossed_up & (close > vwap)
        short_mask = morning & crossed_down & (close < vwap)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        flat = _parse_time(p["flat_time"])
        return pd.Series(df.index.time >= flat, index=df.index)
