"""
ALMA Low Breakout.

Long-only trend-following: enters once the bar's own LOW clears the
ALMA line (a stricter confirmation than a close-based cross -- the
whole bar has to trade above the trend line, not just settle above
it), and exits once the ALMA line itself has been falling for two
bars straight (the trend it was riding has turned down, not just
paused).

Distinct from every other ALMA-adjacent construct in this codebase:
app.indicators.alma exists but had no strategy consuming it -- this
is a plain single-line trend-follow, not a divergence or crossover
system.

Entry: low > ALMA(period, offset, sigma), only while flat.
Exit: ALMA < ALMA one bar ago < ALMA two bars ago (declining for 2
consecutive bars).
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.alma import ALMA
from app.strategies.registry import strategy_registry


@strategy_registry.register("alma_low_breakout")
class ALMALowBreakout(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="alma_low_breakout",
            display_name="ALMA Low Breakout",
            description="Long-only: enters once the bar's own low clears the ALMA trend line, exits once ALMA has declined for two consecutive bars.",
            category="trend_following",
            indicators_used=["alma"],
            default_params={"alma_period": 12, "alma_offset": 0.85, "alma_sigma": 6.0},
            entry_conditions=["low > ALMA(alma_period, alma_offset, alma_sigma), only while flat"],
            exit_conditions=["ALMA has decreased for 2 consecutive bars"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        return ALMA().calculate(
            df, {"period": p["alma_period"], "offset": p["alma_offset"], "sigma": p["alma_sigma"], "source": "close"}
        )

    def _col(self, p: dict[str, Any]) -> str:
        return f"alma_{p['alma_period']}"

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        alma = df[self._col(p)]
        entries = pd.Series(None, index=df.index, dtype=object)
        entries[df["low"] > alma] = TradeDirection.LONG
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        alma = df[self._col(p)]
        return (alma < alma.shift(1)) & (alma.shift(1) < alma.shift(2))
