"""
Minervini Trend Template.

Long-only stock-selection strategy built directly on the
minervini_trend_template indicator's 0-9 criteria score (see that
module's docstring for which of Mark Minervini's 10 original criteria
are and aren't computable from a single symbol's own OHLCV).

Entry and exit use DIFFERENT thresholds on purpose (a hysteresis band,
entry_threshold > exit_threshold) rather than symmetrically requiring
"has it lost qualification": backtesting the earlier symmetric version
(enter at the full 9/9, exit the instant it drops below 9) on both
NVDA daily bars and INFQ intraday bars showed it entering exactly when
the setup completes -- often already extended -- then getting stopped
out within 1-2 bars every time a single criterion flickered (e.g. one
choppy bar pushes SMA50 fractionally below SMA150). A name in a real
Stage 2 uptrend routinely wobbles across 1-2 criteria without the
trend actually breaking down; a 1-point symmetric band was exiting on
noise, not signal. Entry still requires the full, strict qualification
(entry_threshold defaults to 9/9 -- no looser bar to get in), but exit
now waits for a real breakdown (multiple criteria lost, not just one)
before giving up the position.

Entry: minervini_score crosses up to >= entry_threshold (was below it
on the prior bar) -- fires once per fresh qualification, not every bar
it stays qualified.
Exit: minervini_score drops below exit_threshold (< entry_threshold).
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.minervini_trend_template import MinerviniTrendTemplate
from app.strategies.registry import strategy_registry


@strategy_registry.register("minervini_trend_template")
class MinerviniTrendTemplateStrategy(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="minervini_trend_template",
            display_name="Minervini Trend Template",
            description="Long-only: enters on a fresh full (9/9) trend-template qualification, exits only once the score has broken down well below that -- not on the first single criterion that flickers.",
            category="trend_following",
            indicators_used=["minervini_trend_template"],
            default_params={
                "sma_short_period": 50,
                "sma_mid_period": 150,
                "sma_long_period": 200,
                "year_lookback": 252,
                "low_multiple": 1.30,
                "high_fraction": 0.75,
                "sma_long_slope_lookback": 30,
                "entry_threshold": 9,
                "exit_threshold": 7,
            },
            entry_conditions=["minervini_score crosses up to >= entry_threshold (freshly qualifies)"],
            exit_conditions=["minervini_score drops below exit_threshold"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        return MinerviniTrendTemplate().calculate(df, p)

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        score = df["minervini_score"]
        prev_score = score.shift(1).fillna(0)

        freshly_qualifies = (score >= p["entry_threshold"]) & (prev_score < p["entry_threshold"])

        entries = pd.Series(None, index=df.index, dtype=object)
        entries[freshly_qualifies] = TradeDirection.LONG
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        return df["minervini_score"] < p["exit_threshold"]
