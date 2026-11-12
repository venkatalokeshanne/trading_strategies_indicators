"""
RVOL EMA Break.

Ported from a TrendSpider strategy spec: a relative-volume spike
(participation, not a thin tape) on the "wrong" side of a fast EMA
reads as real conviction, not noise. The spec only stated one
condition (RVOL > threshold AND close < EMA) with no direction
attached -- mirrored here around the same EMA rather than guessing
which single direction was meant: short when volume-confirmed
selling pushes price below the EMA, long when volume-confirmed buying
pushes it above (see `direction` param; same mirrored-condition
convention as e.g. donchian_adx_breakout / rvol_breakout in this
codebase). Fires while the condition holds (a plain level condition,
not a fresh-cross event), so re-entry after an exit is possible as
long as it's still true.

The source spec gave no price-based signal exit at all -- every exit
condition it listed (stop-loss, take-profit, trailing-stop, N-candles-
passed) is risk/time management, which in this engine lives in
ExecutionConfig, not hardcoded into a strategy (see e.g.
trend_pullback_adx_confluence's docstring for the same convention).
generate_exits below is a no-op; run this strategy with:
    ExecutionConfig(
        stop_loss_pct=0.015,
        trailing_stop_pct=0.04,
        max_holding_bars=70,
    )
NOTE: this engine's trailing stop SUBSUMES a fixed stop_loss_pct the
moment both are set (whichever trailing/fixed mechanism you configure,
only one governs from entry -- see execution.py's ExecutionConfig
docstring) -- it does not track "whichever of the two is currently
tighter." Setting both stop_loss_pct and trailing_stop_pct as in the
source spec means trailing_stop_pct (4%) is what actually protects the
trade from entry, not the tighter 1.5% figure; call this out if a hard
1.5% floor independent of the trailing stop is what's actually wanted.
take_profit_pct (5.5%) is unaffected by this and applies normally
alongside whichever stop mechanism is active.

Entries also require at least rvol_period bars to have elapsed since
the current session opened. RVOL's own rolling window (see
app.indicators.rvol) is a plain trailing window with no session
boundary awareness -- for the first rvol_period bars of a new session
it's still mostly filled with the PRIOR session's bars, comparing
today's volume against a stale, different-regime baseline. That
structurally inflates RVOL right at the open on ~every session
regardless of whether anything genuine is happening, and it measurably
was: backtesting this strategy on INFQ showed the 09:30 entry bar
alone (the first bar of the session) responsible for 26% of all trades
at a 33% win rate and the single worst per-bucket P&L, while entries
late enough in the session for the window to be entirely built from
that day's own bars performed markedly better. Gating on bar count
(not a clock time) keeps this correct at any interval/session length
rather than hardcoding a time-of-day cutoff tuned to one instrument.

Entry: RVOL(rvol_period) > rvol_threshold AND (close < EMA(ema_period)
for short, close > EMA(ema_period) for long) AND at least rvol_period
bars have elapsed since the session opened.
Exit: none (risk/time-managed only -- see ExecutionConfig above).
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.ema import EMA
from app.indicators.rvol import RelativeVolume
from app.strategies.registry import strategy_registry


@strategy_registry.register("rvol_ema_break")
class RVOLEMABreak(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="rvol_ema_break",
            display_name="RVOL EMA Break",
            description="A relative-volume spike on the 'wrong' side of a fast EMA -- volume-confirmed momentum, mirrored for both long and short. Exits are risk/time-managed via ExecutionConfig, not a price signal.",
            category="momentum",
            indicators_used=["rvol", "ema"],
            default_params={
                "rvol_period": 20,
                "rvol_threshold": 2.5,
                "ema_period": 8,
                "direction": "both",
            },
            entry_conditions=[
                "Short: RVOL(rvol_period) > rvol_threshold AND close < EMA(ema_period)",
                "Long: RVOL(rvol_period) > rvol_threshold AND close > EMA(ema_period)",
                "Either: at least rvol_period bars have elapsed since the session opened "
                "(so RVOL's rolling window isn't still partly built from the prior session)",
            ],
            exit_conditions=[
                "None from this strategy -- run with ExecutionConfig(stop_loss_pct=0.015, "
                "trailing_stop_pct=0.04, max_holding_bars=70) for the source spec's risk/time exits"
            ],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = RelativeVolume().calculate(df, {"period": p["rvol_period"]})
        out = EMA().calculate(out, {"period": p["ema_period"], "source": "close"})
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        rvol = df[f"rvol_{p['rvol_period']}"]
        ema = df[f"ema_{p['ema_period']}"]
        close = df["close"]
        volume_confirmed = rvol > p["rvol_threshold"]

        # 0-indexed position within each calendar-day session -- True
        # once RVOL's own rolling window (rvol_period bars) is built
        # entirely from THIS session's bars, no carryover from the prior
        # one. Works for any DatetimeIndex regardless of bar interval.
        bars_since_session_open = pd.Series(range(len(df)), index=df.index).groupby(df.index.date).cumcount()
        window_is_clean = bars_since_session_open >= p["rvol_period"]

        short_mask = volume_confirmed & (close < ema) & window_is_clean
        long_mask = volume_confirmed & (close > ema) & window_is_clean

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        return pd.Series(False, index=df.index)
