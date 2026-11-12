"""
Squeeze Breakout.

Waits for a volatility squeeze (Bollinger Bands compressed inside
Keltner Channels -- the classic "TTM Squeeze" setup), then enters in
the direction the Squeeze Momentum reading is already leaning the
moment the squeeze releases (the bar the squeeze condition turns
back off after having been on).

Entry: the prior bar was in a squeeze and the current bar isn't
(release), with squeeze momentum positive (long) or negative (short).
Exit: squeeze momentum crosses back through zero.

This file contains ONLY strategy logic -- squeeze/momentum math lives
in app.indicators.squeeze_momentum and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.squeeze_momentum import SqueezeMomentum
from app.strategies.registry import strategy_registry


@strategy_registry.register("squeeze_breakout")
class SqueezeBreakout(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="squeeze_breakout",
            display_name="Squeeze Breakout",
            description="Enters when a Bollinger-inside-Keltner volatility squeeze releases, in the direction momentum already leans.",
            category="breakout",
            indicators_used=["squeeze_momentum"],
            default_params={
                "bb_period": 20,
                "bb_std_dev": 2.0,
                "kc_period": 20,
                "kc_atr_multiple": 1.5,
                "momentum_period": 20,
                "direction": "both",
            },
            entry_conditions=[
                "The squeeze (Bollinger Bands inside Keltner Channels) was on last bar and is off this bar (release)",
                "Long: squeeze momentum is positive at release",
                "Short: squeeze momentum is negative at release",
            ],
            exit_conditions=["Squeeze momentum crosses back through zero"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        return SqueezeMomentum().calculate(
            df,
            {
                "bb_period": p["bb_period"],
                "bb_std_dev": p["bb_std_dev"],
                "kc_period": p["kc_period"],
                "kc_atr_multiple": p["kc_atr_multiple"],
                "momentum_period": p["momentum_period"],
            },
        )

    def _cols(self, p: dict[str, Any]) -> tuple[str, str]:
        return f"squeeze_on_{p['bb_period']}_{p['kc_period']}", f"squeeze_momentum_{p['momentum_period']}"

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        squeeze_col, momentum_col = self._cols(p)
        squeeze_on, momentum = df[squeeze_col], df[momentum_col]

        release = squeeze_on.shift(1, fill_value=False) & ~squeeze_on
        long_mask = release & (momentum > 0)
        short_mask = release & (momentum < 0)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        _, momentum_col = self._cols(p)
        momentum = df[momentum_col]
        prev_momentum = momentum.shift(1)
        return ((momentum > 0) != (prev_momentum > 0)) & prev_momentum.notna()
