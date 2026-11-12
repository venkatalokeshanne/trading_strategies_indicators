"""
ORH Breakout + Relative Volume + VWAP.

An opening-range breakout gated by two independent confirmations
rather than price alone: the breakout bar's own volume must clear a
multiple of the OPENING RANGE'S OWN average per-bar volume (not a
general rolling average -- the baseline is "how busy was this
specific morning," not "how busy is this stock generally"), and close
must sit on the correct side of session VWAP. The breakout is only
armed inside an explicit post-opening-range window, distinct from the
opening range itself, so a close that was already beyond the range
before the window opens doesn't count -- only an actual cross inside
the window does. Reuses app.indicators.opening_range and
app.indicators.vwap as-is; only the volume-confirmation and
window-gating logic is new here.

Source is long-only (breakout above ORH); a mirrored short side
(breakout below the opening-range low, volume-confirmed, close below
VWAP) is added for symmetry with this codebase's other directional
strategies, gated the same way by `direction`.

Entry: inside the breakout window, close crosses above the opening
range high (long) / below the opening range low (short), AND that
bar's volume >= opening-range average volume * volume_multiple, AND
close is above VWAP (long) / below VWAP (short).
Exit: close crosses back through the OPPOSITE side of the opening
range (mirrors app.strategies.orb_breakout's failed-breakout exit).
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.opening_range import OpeningRange
from app.indicators.vwap import VWAP
from app.strategies.registry import strategy_registry
from app.utils.sessions import minutes_since_session_start


@strategy_registry.register("orh_rvol_vwap_breakout")
class ORHRvolVWAPBreakout(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="orh_rvol_vwap_breakout",
            display_name="ORH Breakout + Relative Volume + VWAP",
            description="Opening-range breakout confirmed by volume relative to the opening range's own average and by session VWAP position, armed only inside a post-opening breakout window.",
            category="breakout",
            indicators_used=["opening_range", "vwap"],
            default_params={
                "opening_range_minutes": 30,
                "breakout_window_end_minutes": 120,
                "volume_multiple": 1.5,
                "direction": "both",
            },
            entry_conditions=[
                "Long: inside the breakout window, close crosses above the opening range high, bar volume >= opening-range average volume * volume_multiple, and close > VWAP",
                "Short: inside the breakout window, close crosses below the opening range low, bar volume >= opening-range average volume * volume_multiple, and close < VWAP",
            ],
            exit_conditions=["close crosses back through the opposite side of the opening range (the breakout failed)"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("ORHRvolVWAPBreakout requires a DatetimeIndex.")
        out = OpeningRange().calculate(df, {"minutes": p["opening_range_minutes"]})
        out = VWAP().calculate(out, {})

        # Average volume of ONLY the opening-range bars, broadcast to every
        # bar of that day. groupby(...).transform("mean") skips the NaN
        # (outside-window) rows when computing the mean but still fills
        # them in with the result -- exactly the "freeze after the window
        # closes" behavior the source achieves with an explicit var/if.
        day = out.index.date
        in_opening_window = minutes_since_session_start(out.index) < p["opening_range_minutes"]
        masked_volume = out["volume"].where(in_opening_window)
        out["orv_opening_avg_volume"] = masked_volume.groupby(day).transform("mean")
        return out

    def _cols(self, p: dict[str, Any]) -> tuple[str, str]:
        m = p["opening_range_minutes"]
        return f"or_high_{m}", f"or_low_{m}"

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        high_col, low_col = self._cols(p)
        or_high, or_low = df[high_col], df[low_col]
        close, prev_close = df["close"], df["close"].shift(1)
        vwap = df["vwap"]

        mins_since_start = minutes_since_session_start(df.index)
        in_breakout_window = (mins_since_start >= p["opening_range_minutes"]) & (
            mins_since_start < p["breakout_window_end_minutes"]
        )
        volume_confirmed = df["volume"] >= df["orv_opening_avg_volume"] * p["volume_multiple"]

        long_mask = (
            in_breakout_window
            & (close > or_high)
            & (prev_close <= or_high)
            & volume_confirmed
            & (close > vwap)
        )
        short_mask = (
            in_breakout_window
            & (close < or_low)
            & (prev_close >= or_low)
            & volume_confirmed
            & (close < vwap)
        )

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        high_col, low_col = self._cols(p)
        or_high, or_low = df[high_col], df[low_col]
        close, prev_close = df["close"], df["close"].shift(1)

        long_failed = (close < or_low) & (prev_close >= or_low)
        short_failed = (close > or_high) & (prev_close <= or_high)
        return long_failed | short_failed
