"""
Opening Range Breakout, midpoint stop (the trader-scanner / trader-entry / trader-exit plan).

The first N minutes set the range. The plan is long-only, as the trader-* skills are:
enter on the first 5-minute close above the range high, before the entry cutoff.
The stop is the MIDPOINT of the range, not the far side: the trade is wrong as soon as price
gives back half the range. Everything is flat by the flat_time bar's close.

Entry: first close above the opening-range high after the window has closed, and before entry_cutoff.
Exit:  close back below the range midpoint (the stop, read on closes), or the flat_time bar.
The 2R profit target of the plan is a risk setting, not a signal, so it lives in Execution
Settings (take-profit) and is applied to every strategy the same way.

Only strategy logic lives here; the range math is app.indicators.opening_range.
"""

from datetime import datetime, time
from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.opening_range import OpeningRange
from app.strategies.registry import strategy_registry
from app.utils.sessions import minutes_since_session_start


def _t(value: str) -> time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Expected a time in 'HH:MM' 24h format, got {value!r}.") from exc


@strategy_registry.register("orb_midpoint_stop")
class ORBMidpointStop(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="orb_midpoint_stop",
            display_name="ORB, midpoint stop (long)",
            description=(
                "Long-only opening-range breakout from the trader-* plan: first close above the 15-minute range high "
                "before the cutoff, stop at the range midpoint, flat by 15:55."
            ),
            category="breakout",
            indicators_used=["opening_range"],
            default_params={"minutes": 15, "entry_cutoff": "11:30", "flat_time": "15:50"},
            entry_conditions=[
                "The opening window has closed",
                "Close crosses above the opening-range high (previous close at or below it)",
                "The bar is before entry_cutoff",
            ],
            exit_conditions=[
                "Close below the opening-range midpoint (stop)",
                "Close of the flat_time bar (15:50 bar on 5-minute data = flat at 15:55)",
            ],
        )

    def validate_params(self, params: dict[str, Any]) -> dict[str, Any]:
        p = super().validate_params(params)
        _t(p["entry_cutoff"])
        _t(p["flat_time"])
        return p

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        return OpeningRange().calculate(df, {"minutes": p["minutes"]})

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        m = p["minutes"]
        or_high = df[f"or_high_{m}"]
        close, prev_close = df["close"], df["close"].shift(1)
        window_closed = minutes_since_session_start(df.index) >= m
        early = pd.Series(df.index.time < _t(p["entry_cutoff"]), index=df.index)
        long_mask = window_closed & early & (close > or_high) & (prev_close <= or_high)
        entries = pd.Series(None, index=df.index, dtype=object)
        entries[long_mask] = TradeDirection.LONG
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        m = p["minutes"]
        mid = (df[f"or_high_{m}"] + df[f"or_low_{m}"]) / 2
        close = df["close"]
        stopped = (close < mid) & (close.shift(1) >= mid)
        flat = pd.Series(df.index.time >= _t(p["flat_time"]), index=df.index)
        return stopped | flat
