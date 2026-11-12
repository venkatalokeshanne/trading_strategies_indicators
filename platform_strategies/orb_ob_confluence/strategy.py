"""
ORB + Order Block Confluence.

A new strategy, not a re-tuning of an existing one: it fuses the two
signals that independently ranked best/second-best on INFQ's 5-minute
bars (Opening Range Breakout and Order Block Retest) into a single
stricter entry -- the read being that a clean opening-range breakout is
more likely to run (rather than round-trip and fail) when it already
has institutional footprint behind it, i.e. a still-fresh order block
in the SAME direction as the break.

Entry: the opening window has closed AND price closes beyond the
opening range (long: above the high, short: below the low) AND a
still-fresh order block in that same direction is currently active
(the forward-filled zone from app.indicators.order_blocks, capped at
max_zone_age_bars -- same mechanism app.strategies.order_block_retest
uses).
Exit: the ORB breakout round-trips back through the opposite opening-
range level (the breakout failed) -- same exit as plain orb_breakout.
An earlier version also exited on order-block invalidation (mirroring
order_block_retest's own exit); backtesting showed that made things
strictly worse here (net profit dropped from ~$15.2k to ~$858 on INFQ
5min, most trades cut short via premature signal_exit instead of
running to their stop/target) -- the confluence idea only pays off as
an ENTRY filter, not as an additional exit trigger, so it was dropped.

This file contains ONLY strategy logic -- both indicators
(opening_range, order_blocks) are reused as-is from their existing
modules, composed here rather than duplicated.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.opening_range import OpeningRange
from app.indicators.order_blocks import OrderBlocks
from app.strategies.registry import strategy_registry
from app.utils.sessions import minutes_since_session_start


@strategy_registry.register("orb_ob_confluence")
class ORBOrderBlockConfluence(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="orb_ob_confluence",
            display_name="ORB + Order Block Confluence",
            description=(
                "Opening range breakout, taken only when a still-fresh order block in the same "
                "direction already backs the move -- structure confirming the breakout instead of "
                "trading the range break alone."
            ),
            category="breakout",
            indicators_used=["opening_range", "order_blocks"],
            default_params={
                "minutes": 15,
                "atr_period": 14,
                "impulse_bars": 5,
                "impulse_atr_multiple": 2.0,
                "max_zone_age_bars": 100,
                "direction": "both",
            },
            live_caution=(
                "The order-block half of this confluence check only becomes valid once price has "
                "already displaced away from it, so the confirming zone is known well after the fact; "
                "real fills will typically land later and worse than the backtest assumes."
            ),
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = OpeningRange().calculate(df, {"minutes": p["minutes"]})
        out = OrderBlocks().calculate(
            out,
            {
                "atr_period": p["atr_period"],
                "impulse_bars": p["impulse_bars"],
                "impulse_atr_multiple": p["impulse_atr_multiple"],
            },
        )
        limit = p["max_zone_age_bars"]
        # Same forward-fill-with-cap as order_block_retest.prepare -- a
        # zone is only flagged on its formation bar; this lets later
        # bars still treat it as "currently active" up to `limit` bars
        # afterward instead of only on that single bar.
        for col in ("bullish_ob_top", "bullish_ob_bottom", "bearish_ob_top", "bearish_ob_bottom"):
            out[col] = out[col].ffill(limit=limit)
        return out

    def _orb_cols(self, p: dict[str, Any]) -> tuple[str, str]:
        m = p["minutes"]
        return f"or_high_{m}", f"or_low_{m}"

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        high_col, low_col = self._orb_cols(p)
        or_high, or_low = df[high_col], df[low_col]
        close, prev_close = df["close"], df["close"].shift(1)
        window_closed = minutes_since_session_start(df.index) >= p["minutes"]

        broke_up = window_closed & (close > or_high) & (prev_close <= or_high)
        broke_down = window_closed & (close < or_low) & (prev_close >= or_low)

        # The confluence filter: a fresh order block in the SAME
        # direction must already be active -- structure backing the
        # breakout, not just a raw range break.
        bullish_active = df["bullish_ob_top"].notna()
        bearish_active = df["bearish_ob_top"].notna()

        long_mask = broke_up & bullish_active
        short_mask = broke_down & bearish_active

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        high_col, low_col = self._orb_cols(p)
        or_high, or_low = df[high_col], df[low_col]
        close, prev_close = df["close"], df["close"].shift(1)

        orb_long_failed = (close < or_low) & (prev_close >= or_low)
        orb_short_failed = (close > or_high) & (prev_close <= or_high)

        return orb_long_failed | orb_short_failed
