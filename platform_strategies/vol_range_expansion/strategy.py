"""
Volume-Confirmed Range Expansion.

Built FROM real INFQ 5-minute data (2026-05-11 to 2026-08-05, the actual
dxFeed intraday retention window -- INFQ trades further back on daily
bars but 5min history doesn't go back further), not from combining
already-written strategies. Exploratory analysis on that data surfaced
two independently-sized-enough findings this strategy is built around:

  1. A volume spike (z > 2 vs its own rolling average) precedes a next
     bar roughly 2.5x the baseline size (125bps vs 49bps avg |return|,
     n=262 spikes across 60 sessions).
  2. A bar with an unusually wide true range (z > 1.5) shows real
     continuation over the next 3 bars, most clearly to the downside
     (avg +12.5bps after a big up-bar vs -40.7bps after a big down-bar,
     against a ~0bps baseline).

Deliberately NOT built on the day-of-week pattern also found in the
same analysis (Wed/Fri strongly negative, Mon/Thu positive) -- that
split only has 10-13 sessions per weekday, too thin to trust; baking
it in would be the same hindsight-overfitting trap flagged earlier
this session, just moved one level down.

Entry: a bar's true range AND volume are both simultaneously elevated
(their own rolling z-scores exceed range_z_threshold / vol_z_threshold)
-- a genuine expansion move, not just a big range OR just high volume
alone. Direction follows the bar's own close vs open.
Exit: the expansion has cooled off -- both z-scores have dropped back
below their rolling average (z < 0). Backstopped by the shared ATR
stop/target/session-close bracket like every other strategy here.

This file contains ONLY strategy logic -- true_range is reused as-is
from app.indicators._shared; the rolling z-score composition on top of
it is specific to this strategy, not duplicated general indicator math.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators._shared import true_range
from app.strategies.registry import strategy_registry


@strategy_registry.register("vol_range_expansion")
class VolRangeExpansion(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="vol_range_expansion",
            display_name="Volume-Confirmed Range Expansion",
            description=(
                "Trades a bar where true range AND volume are both simultaneously elevated vs. their own "
                "rolling average -- a genuine expansion move, not a big range or high volume alone."
            ),
            category="volatility",
            indicators_used=["trange"],
            default_params={
                "lookback": 78,  # ~one regular session at 5min
                "range_z_threshold": 1.5,
                "vol_z_threshold": 2.0,
                "direction": "both",
            },
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = df.copy()
        lb = p["lookback"]

        tr = true_range(out)
        tr_mean = tr.rolling(lb, min_periods=lb).mean()
        tr_std = tr.rolling(lb, min_periods=lb).std()
        out["range_z"] = (tr - tr_mean) / tr_std.replace(0, pd.NA)

        vol_mean = out["volume"].rolling(lb, min_periods=lb).mean()
        vol_std = out["volume"].rolling(lb, min_periods=lb).std()
        out["vol_z"] = (out["volume"] - vol_mean) / vol_std.replace(0, pd.NA)
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        range_z, vol_z = df["range_z"], df["vol_z"]
        close, open_ = df["close"], df["open"]

        expansion = (range_z > p["range_z_threshold"]) & (vol_z > p["vol_z_threshold"])
        long_mask = expansion & (close > open_)
        short_mask = expansion & (close < open_)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        range_z, vol_z = df["range_z"], df["vol_z"]
        return (range_z < 0) & (vol_z < 0)
