"""
CCI Extreme Reversal.

CCI reverting back inside its own +/-100 band after pushing beyond it
is a long-standing day-trading reversal read: the push beyond +/-100
marks an unusually large deviation from the recent average price, and
the snap back inside the band marks that deviation fading.

Entry: CCI crosses back above -100 from below (long); crosses back
below +100 from above (short).
Exit: CCI reaches the opposite extreme band.

This file contains ONLY strategy logic -- CCI math lives in
app.indicators.cci and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.cci import CCI
from app.strategies.registry import strategy_registry


@strategy_registry.register("cci_extreme_reversal")
class CCIExtremeReversal(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="cci_extreme_reversal",
            display_name="CCI Extreme Reversal",
            description="Trades CCI snapping back inside its own +/-100 band after an extreme push beyond it.",
            category="mean_reversion",
            indicators_used=["cci"],
            default_params={"period": 20, "extreme": 100.0, "direction": "both"},
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        return CCI().calculate(df, {"period": p["period"]})

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        cci = df[f"cci_{p['period']}"]
        prev_cci = cci.shift(1)
        extreme = p["extreme"]

        long_mask = (cci > -extreme) & (prev_cci <= -extreme)
        short_mask = (cci < extreme) & (prev_cci >= extreme)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        cci = df[f"cci_{p['period']}"]
        prev_cci = cci.shift(1)
        extreme = p["extreme"]
        reaches_upper_extreme = (cci > extreme) & (prev_cci <= extreme)
        reaches_lower_extreme = (cci < -extreme) & (prev_cci >= -extreme)
        return reaches_upper_extreme | reaches_lower_extreme
