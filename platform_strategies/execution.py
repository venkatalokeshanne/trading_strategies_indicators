"""
Trade simulation engine.

Takes a strategy's entry/exit signals and turns them into a sequence
of Trades, applying execution realism (commission, slippage, forced
intraday close, and optional risk management). This is intentionally
the ONLY place that understands "what does it mean to hold a
position" — strategies just emit signals.

Kept here (not inside Strategy subclasses) so every strategy gets
identical execution behavior, and improvements to fill/commission/risk
modeling benefit every strategy at once.
"""

import logging
from dataclasses import dataclass
from datetime import time as time_cls

import pandas as pd

from app.domain.interfaces.strategy import Trade, TradeDirection

logger = logging.getLogger(__name__)
from app.indicators.atr import ATR
from app.utils.sessions import is_last_bar_of_session


@dataclass(frozen=True)
class ExecutionConfig:
    """Runner-level execution settings (NOT strategy parameters)."""

    capital: float = 10_000.0
    quantity: float = 1.0
    commission_per_trade: float = 0.0  # flat, applied once per round-trip -- 0 is realistic for most commission-free retail brokers today
    # 0.05% per fill (~0.1% round-trip) -- a conservative stand-in for
    # bid-ask spread/market-impact cost that a raw close-price fill
    # otherwise assumes away for free. Real cost varies a lot by
    # instrument liquidity; override per backtest if you have a better
    # estimate for what you actually trade.
    slippage_pct: float = 0.0005  # fraction of price, applied unfavorably on fills
    force_close_at_session_end: bool = True

    # Jev (TypeSafe System One) review of entries and brackets. Plain data
    # only -- the advisor is built inside the worker process, because this
    # config is pickled across the backtest process pool.
    #   "off"     -- untouched, the default
    #   "review"  -- an entry is skipped unless Jev puts the trade's own
    #                direction at or above jev_min_probability
    #   "bracket" -- the stop and target come from Jev's 80% band
    #   "both"    -- review and bracket
    jev_mode: str = "off"
    jev_min_probability: float = 0.55
    # Answer only from the cache; a state never seen before is treated as
    # "no opinion" and the entry is left exactly as the strategy made it.
    jev_offline: bool = False

    # Which price a signal actually fills at.
    #   "close"     -- fill on the signal bar's own close (this engine's
    #                  original behaviour; kept as the default so every
    #                  pre-existing strategy and test is unaffected).
    #   "next_open" -- the signal is confirmed at the signal bar's close
    #                  and filled at the NEXT bar's open. This is what
    #                  TrendSpider does (its strategies carry
    #                  priceSource: "open"), so the ported TrendSpider
    #                  strategies must use it or every entry and exit
    #                  price is wrong. It is also the more honest model
    #                  in general: you cannot transact at a close you
    #                  only know once the bar has already ended.
    fill_at: str = "close"  # "close" | "next_open"

    # Data-fetch scope, NOT execution behavior -- carried here only so
    # these travel through the same execution-settings plumbing as
    # every other execution setting. Actually applied by
    # app.integrations.twelvedata_client.fetch_historical_bars (and its
    # filter_by_session helper), not by anything in this module.
    include_extended_hours: bool = False
    include_overnight: bool = False

    # Global trade-direction filter, applied uniformly on top of whatever
    # a strategy's own params allow (e.g. ORB's "direction" param). Lives
    # here rather than per-strategy so "only take longs" works the same
    # way for every strategy without each one reimplementing it.
    direction_filter: str = "both"  # "long_only" | "short_only" | "both"

    # Global entry-time-of-day gate, same "applied uniformly on top of
    # the strategy's own signals" idea as direction_filter -- suppress
    # entries taken outside a clock window (e.g. "only the first two
    # hours of the session") without each strategy reimplementing it.
    # Both None (the default) is a no-op; both must be set together.
    # "HH:MM", America/New_York, matching every other session time in
    # this app (see app.integrations.twelvedata_client's session
    # constants). Exits are never affected -- a position opened inside
    # the window is still managed/exited normally if it's still open
    # once the clock moves past entry_time_end.
    entry_time_start: str | None = None
    entry_time_end: str | None = None

    # Risk management — all disabled by default (None) so existing
    # behavior is unchanged unless a caller opts in.
    atr_period: int = 14  # inert unless a *_atr_multiple field below is set
    stop_loss_atr_multiple: float | None = None
    stop_loss_pct: float | None = None  # flat % of entry price; e.g. 0.01 = 1%
    take_profit_atr_multiple: float | None = None
    take_profit_pct: float | None = None  # flat % of entry price, same idea as stop_loss_pct
    trailing_stop_atr_multiple: float | None = None  # if set, takes precedence over stop_loss_atr_multiple/stop_loss_pct
    trailing_stop_pct: float | None = None  # flat-%-of-entry-price trailing distance, same precedence tier as trailing_stop_atr_multiple
    # Exit after this many bars in the trade, regardless of P&L or any
    # other exit condition -- a plain time stop (e.g. TrendSpider's
    # "Exit after N candles, for any PnL"). Independent of every other
    # field here: checked alongside force_close_at_session_end, not as
    # part of the stop/target intrabar risk check.
    max_holding_bars: int | None = None
    risk_per_trade_pct: float | None = None  # requires a stop (atr_multiple, pct, or trailing) to be set
    # Cap quantity so entry position value never exceeds capital * this
    # (1.0 = full capital, i.e. no leverage). Applied to BOTH fixed and
    # risk-based sizing — risk sizing on a tight stop can otherwise
    # imply a position worth many times the account.
    max_position_value_pct: float | None = None

    # Priority when multiple stop mechanisms are configured at once:
    # (trailing_stop_atr_multiple or trailing_stop_pct) > stop_loss_pct
    # > stop_loss_atr_multiple -- a trailing stop, ATR- or pct-based,
    # still fully SUBSUMES a fixed stop the moment both are set (it
    # governs alone from entry, not "whichever is tighter"); set only
    # one of the two trailing fields, and only one of the two fixed-stop
    # fields, per backtest. stop_loss_pct/take_profit_pct/
    # trailing_stop_pct are intentionally independent of ATR — they
    # never need a valid ATR reading, unlike the *_atr_multiple fields.


def _parse_time(value: str, field_name: str) -> time_cls:
    try:
        hour_str, minute_str = value.split(":")
        return time_cls(int(hour_str), int(minute_str))
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"{field_name} must be an 'HH:MM' string (got {value!r}).") from exc


def _risk_management_enabled(config: ExecutionConfig) -> bool:
    return (
        config.stop_loss_atr_multiple is not None
        or config.stop_loss_pct is not None
        or config.take_profit_atr_multiple is not None
        or config.take_profit_pct is not None
        or config.trailing_stop_atr_multiple is not None
        or config.trailing_stop_pct is not None
    )


def _validate_config(config: ExecutionConfig) -> None:
    if config.jev_mode not in ("off", "review", "bracket", "both"):
        raise ValueError(f'jev_mode must be "off", "review", "bracket" or "both" (got {config.jev_mode!r}).')
    if not 0.0 <= config.jev_min_probability <= 1.0:
        raise ValueError("jev_min_probability must be between 0 and 1.")
    if (
        config.risk_per_trade_pct is not None
        and config.stop_loss_atr_multiple is None
        and config.stop_loss_pct is None
        and config.trailing_stop_atr_multiple is None
        and config.trailing_stop_pct is None
    ):
        raise ValueError(
            "risk_per_trade_pct requires stop_loss_atr_multiple, stop_loss_pct, "
            "trailing_stop_atr_multiple, or trailing_stop_pct to be set."
        )
    if config.stop_loss_pct is not None and config.stop_loss_pct <= 0:
        raise ValueError(f"stop_loss_pct must be > 0 (got {config.stop_loss_pct!r}).")
    if config.take_profit_pct is not None and config.take_profit_pct <= 0:
        raise ValueError(f"take_profit_pct must be > 0 (got {config.take_profit_pct!r}).")
    if config.trailing_stop_pct is not None and config.trailing_stop_pct <= 0:
        raise ValueError(f"trailing_stop_pct must be > 0 (got {config.trailing_stop_pct!r}).")
    if config.max_holding_bars is not None and config.max_holding_bars <= 0:
        raise ValueError(f"max_holding_bars must be > 0 (got {config.max_holding_bars!r}).")
    if config.max_position_value_pct is not None and config.max_position_value_pct <= 0:
        raise ValueError(f"max_position_value_pct must be > 0 (got {config.max_position_value_pct!r}).")
    if config.direction_filter not in ("long_only", "short_only", "both"):
        raise ValueError(
            f"direction_filter must be 'long_only', 'short_only', or 'both' (got {config.direction_filter!r})."
        )
    if (config.entry_time_start is None) != (config.entry_time_end is None):
        raise ValueError("entry_time_start and entry_time_end must both be set, or both left unset.")
    if config.entry_time_start is not None:
        start = _parse_time(config.entry_time_start, "entry_time_start")
        end = _parse_time(config.entry_time_end, "entry_time_end")
        if start >= end:
            raise ValueError(
                f"entry_time_start must be before entry_time_end (got {config.entry_time_start!r}, {config.entry_time_end!r})."
            )


def _apply_direction_filter(entries: pd.Series, direction_filter: str) -> pd.Series:
    """Drop entry signals that don't match the allowed direction, leaving
    everything else (including exits) untouched.

    Uses element-wise .map (not a vectorized comparison) because
    TradeDirection is a str Enum: pandas can infer a specialized string
    dtype for an entries Series built without an explicit dtype=object,
    under which a vectorized `series != TradeDirection.X` silently
    compares wrong and matches everything.
    """
    if direction_filter == "both":
        return entries
    disallowed = TradeDirection.SHORT if direction_filter == "long_only" else TradeDirection.LONG
    return entries.map(lambda v: None if v == disallowed else v).astype(object)


def _apply_time_window_filter(entries: pd.Series, df: pd.DataFrame, config: ExecutionConfig) -> pd.Series:
    """Drop entry signals taken outside [entry_time_start, entry_time_end),
    leaving everything else (including exits) untouched. Same shape as
    _apply_direction_filter, and a no-op when both are unset (the default).
    """
    if config.entry_time_start is None:
        return entries
    if not isinstance(df.index, pd.DatetimeIndex):
        return entries
    start = _parse_time(config.entry_time_start, "entry_time_start")
    end = _parse_time(config.entry_time_end, "entry_time_end")
    times = pd.Series(df.index, index=df.index).dt.time
    in_window = (times >= start) & (times < end)
    return entries.where(in_window, None).astype(object)


def _fill_price(price: float, direction: TradeDirection, *, entering: bool, slippage_pct: float) -> float:
    """
    Apply slippage unfavorably: buys fill higher, sells fill lower.

    entering=True + LONG  -> buy  -> price up
    entering=True + SHORT -> sell -> price down
    entering=False (exit) + LONG  -> sell -> price down
    entering=False (exit) + SHORT -> buy  -> price up
    """
    is_buy = (direction == TradeDirection.LONG) == entering
    factor = 1 + slippage_pct if is_buy else 1 - slippage_pct
    return price * factor


def _pnl(direction: TradeDirection, entry_price: float, exit_price: float, quantity: float) -> float:
    if direction == TradeDirection.LONG:
        return (exit_price - entry_price) * quantity
    return (entry_price - exit_price) * quantity


def simulate_trades(
    df: pd.DataFrame,
    entries: pd.Series,
    exits: pd.Series,
    config: ExecutionConfig = ExecutionConfig(),
) -> list[Trade]:
    """
    Sequentially walk the bars, maintaining at most one open position
    at a time (no pyramiding/averaging in v1 — keeps results easy to
    reason about and compare across strategies).

    Args:
        df: indicator-enriched OHLCV dataframe (DatetimeIndex). Only
            needs a "close" column unless risk management (stop-loss /
            take-profit / trailing-stop) is enabled via config, in
            which case "high" and "low" are also required.
        entries: object Series of TradeDirection | None, from generate_entries.
        exits: boolean Series, from generate_exits.
        config: execution realism + risk-management settings.

    Returns:
        List of completed Trade objects (any position still open at
        the end of the data is force-closed at the last price).
    """
    if len(df) != len(entries) or len(df) != len(exits):
        raise ValueError("df, entries, and exits must be the same length.")

    _validate_config(config)
    entries = _apply_direction_filter(entries, config.direction_filter)
    entries = _apply_time_window_filter(entries, df, config)

    # "Signal at bar i's close, fill at bar i+1's open" is expressed by
    # shifting the signals forward one bar and reading the OPEN column:
    # the shifted signal now sits on the bar it actually fills in, so the
    # rest of the loop (stops, targets, session close, holding period)
    # measures from the real fill bar without any special-casing.
    if config.fill_at == "next_open":
        if "open" not in df.columns:
            raise ValueError('fill_at="next_open" requires an "open" column.')
        entries = entries.shift(1)
        exits = exits.shift(1).fillna(False).astype(bool)
        fill_reference = df["open"]
    elif config.fill_at == "close":
        fill_reference = df["close"]
    else:
        raise ValueError(f'fill_at must be "close" or "next_open" (got {config.fill_at!r}).')

    forced_close = (
        is_last_bar_of_session(df.index)
        if config.force_close_at_session_end and isinstance(df.index, pd.DatetimeIndex)
        else pd.Series(False, index=df.index)
    )

    risk_enabled = _risk_management_enabled(config)
    atr_series = None
    if risk_enabled:
        atr_col = f"atr_{config.atr_period}"
        atr_series = ATR().calculate(df, {"period": config.atr_period})[atr_col]

    jev = _jev_gate(config, df)

    trades: list[Trade] = []
    open_direction: TradeDirection | None = None
    open_entry_time = None
    open_entry_price = None
    open_entry_index: int | None = None
    open_quantity = config.quantity
    open_stop_price: float | None = None
    open_trailing_price: float | None = None
    open_trailing_distance: float | None = None
    open_target_price: float | None = None

    def _reset_open_state() -> None:
        nonlocal open_direction, open_entry_time, open_entry_price, open_entry_index
        nonlocal open_quantity, open_stop_price, open_trailing_price, open_trailing_distance, open_target_price
        open_direction = None
        open_entry_time = None
        open_entry_price = None
        open_entry_index = None
        open_quantity = config.quantity
        open_stop_price = None
        open_trailing_price = None
        open_trailing_distance = None
        open_target_price = None

    for i, ts in enumerate(df.index):
        # The price a fill on THIS bar happens at: the bar's close under
        # fill_at="close", or its open under fill_at="next_open" (where
        # the signals were already shifted onto this bar).
        close_price = fill_reference.iloc[i]

        if open_direction is not None:
            # 1. Intrabar stop-loss / take-profit / trailing-stop check (never on the entry bar itself).
            stop_hit = False
            target_hit = False
            risk_exit_price = None
            risk_exit_reason = None

            if risk_enabled and i > open_entry_index:
                bar_high = df["high"].iloc[i]
                bar_low = df["low"].iloc[i]

                if open_trailing_price is not None:
                    if open_direction == TradeDirection.LONG:
                        open_trailing_price = max(open_trailing_price, bar_high - open_trailing_distance)
                    else:
                        open_trailing_price = min(open_trailing_price, bar_low + open_trailing_distance)

                # A fixed stop and a trailing stop are mutually exclusive per trade
                # (trailing subsumes the fixed stop at entry) -- exactly one of
                # these two is ever set for a given open position.
                active_stop_price = open_trailing_price if open_trailing_price is not None else open_stop_price
                if active_stop_price is not None:
                    if open_direction == TradeDirection.LONG and bar_low <= active_stop_price:
                        stop_hit = True
                    elif open_direction == TradeDirection.SHORT and bar_high >= active_stop_price:
                        stop_hit = True
                    if stop_hit:
                        risk_exit_price = active_stop_price
                        risk_exit_reason = "trailing_stop" if open_trailing_price is not None else "stop_loss"

                # Take-profit only checked if the stop didn't already fire this bar --
                # conservative assumption when a single bar's range could plausibly
                # have hit both (OHLC data can't tell us which came first intrabar).
                if not stop_hit and open_target_price is not None:
                    if open_direction == TradeDirection.LONG and bar_high >= open_target_price:
                        target_hit = True
                    elif open_direction == TradeDirection.SHORT and bar_low <= open_target_price:
                        target_hit = True
                    if target_hit:
                        risk_exit_price = open_target_price
                        risk_exit_reason = "take_profit"

            if stop_hit or target_hit:
                fill = _fill_price(risk_exit_price, open_direction, entering=False, slippage_pct=config.slippage_pct)
                pnl = _pnl(open_direction, open_entry_price, fill, open_quantity) - config.commission_per_trade
                trades.append(
                    Trade(
                        entry_time=open_entry_time,
                        exit_time=ts,
                        direction=open_direction,
                        entry_price=open_entry_price,
                        exit_price=fill,
                        quantity=open_quantity,
                        pnl=pnl,
                        exit_reason=risk_exit_reason,
                    )
                )
                _reset_open_state()
                continue  # don't re-enter on the same bar we just exited

            # 2. Signal exit / forced session close / max-holding-bars time stop
            #    (intrabar risk exits above take priority over all three of these).
            max_hold_exceeded = (
                config.max_holding_bars is not None and (i - open_entry_index) >= config.max_holding_bars
            )
            exit_now = bool(exits.iloc[i]) or bool(forced_close.iloc[i]) or max_hold_exceeded
            if exit_now:
                if exits.iloc[i]:
                    reason = "signal_exit"
                elif forced_close.iloc[i]:
                    reason = "forced_session_close"
                else:
                    reason = "max_holding_bars_exceeded"
                fill = _fill_price(close_price, open_direction, entering=False, slippage_pct=config.slippage_pct)
                pnl = _pnl(open_direction, open_entry_price, fill, open_quantity) - config.commission_per_trade
                trades.append(
                    Trade(
                        entry_time=open_entry_time,
                        exit_time=ts,
                        direction=open_direction,
                        entry_price=open_entry_price,
                        exit_price=fill,
                        quantity=open_quantity,
                        pnl=pnl,
                        exit_reason=reason,
                    )
                )
                _reset_open_state()
                continue  # don't re-enter on the same bar we just exited

        if open_direction is None:
            signal = entries.iloc[i]
            if signal in (TradeDirection.LONG, TradeDirection.SHORT) and jev is not None:
                signal = jev.review(i, signal)
            if signal in (TradeDirection.LONG, TradeDirection.SHORT):
                open_direction = signal
                open_entry_time = ts
                open_entry_index = i
                open_entry_price = _fill_price(
                    close_price, signal, entering=True, slippage_pct=config.slippage_pct
                )

                stop_distance_for_sizing = None
                if risk_enabled:
                    # ATR is NaN during the indicator's warm-up window; treat
                    # ATR-based stop/target/trailing as disabled for THIS
                    # trade only rather than crashing or sizing against a
                    # NaN distance. stop_loss_pct never depends on ATR, so
                    # it's handled outside this validity check.
                    entry_atr = atr_series.iloc[i]
                    atr_valid = pd.notna(entry_atr) and entry_atr > 0

                    if config.trailing_stop_atr_multiple is not None and atr_valid:
                        open_trailing_distance = entry_atr * config.trailing_stop_atr_multiple
                        open_trailing_price = (
                            open_entry_price - open_trailing_distance
                            if signal == TradeDirection.LONG
                            else open_entry_price + open_trailing_distance
                        )
                        stop_distance_for_sizing = open_trailing_distance
                    elif config.trailing_stop_pct is not None:
                        open_trailing_distance = open_entry_price * config.trailing_stop_pct
                        open_trailing_price = (
                            open_entry_price - open_trailing_distance
                            if signal == TradeDirection.LONG
                            else open_entry_price + open_trailing_distance
                        )
                        stop_distance_for_sizing = open_trailing_distance
                    elif config.stop_loss_pct is not None:
                        stop_distance = open_entry_price * config.stop_loss_pct
                        open_stop_price = (
                            open_entry_price - stop_distance
                            if signal == TradeDirection.LONG
                            else open_entry_price + stop_distance
                        )
                        stop_distance_for_sizing = stop_distance
                    elif config.stop_loss_atr_multiple is not None and atr_valid:
                        stop_distance = entry_atr * config.stop_loss_atr_multiple
                        open_stop_price = (
                            open_entry_price - stop_distance
                            if signal == TradeDirection.LONG
                            else open_entry_price + stop_distance
                        )
                        stop_distance_for_sizing = stop_distance

                    if config.take_profit_atr_multiple is not None and atr_valid:
                        target_distance = entry_atr * config.take_profit_atr_multiple
                        open_target_price = (
                            open_entry_price + target_distance
                            if signal == TradeDirection.LONG
                            else open_entry_price - target_distance
                        )
                    elif config.take_profit_pct is not None:
                        target_distance = open_entry_price * config.take_profit_pct
                        open_target_price = (
                            open_entry_price + target_distance
                            if signal == TradeDirection.LONG
                            else open_entry_price - target_distance
                        )

                if jev is not None:
                    # Jev's 80% band replaces the ATR bracket when asked to.
                    # Sizing below then risks the same capital against Jev's
                    # own stop distance, so the two stay consistent.
                    bracket = jev.bracket(i, signal, open_entry_price)
                    if bracket is not None:
                        open_stop_price, open_target_price = bracket
                        open_trailing_price = open_trailing_distance = None
                        stop_distance_for_sizing = abs(open_entry_price - open_stop_price) or None

                if config.risk_per_trade_pct is not None and stop_distance_for_sizing:
                    open_quantity = (config.capital * config.risk_per_trade_pct) / stop_distance_for_sizing
                else:
                    open_quantity = config.quantity

                if config.max_position_value_pct is not None and open_entry_price > 0:
                    max_quantity = (config.capital * config.max_position_value_pct) / open_entry_price
                    open_quantity = min(open_quantity, max_quantity)

    # Any position still open at the end of the data: force-close at the last bar.
    if open_direction is not None:
        last_price = df["close"].iloc[-1]
        fill = _fill_price(last_price, open_direction, entering=False, slippage_pct=config.slippage_pct)
        pnl = _pnl(open_direction, open_entry_price, fill, open_quantity) - config.commission_per_trade
        trades.append(
            Trade(
                entry_time=open_entry_time,
                exit_time=df.index[-1],
                direction=open_direction,
                entry_price=open_entry_price,
                exit_price=fill,
                quantity=open_quantity,
                pnl=pnl,
                exit_reason="end_of_data",
            )
        )

    return trades



class _JevGate:
    """Consults Jev at the moment an entry would be taken.

    Built per simulate_trades call (inside the worker process -- the
    advisor holds a sqlite handle and must not cross a pickle boundary).
    A state Jev has no answer for, or any transport failure, leaves the
    strategy's own decision untouched: the model can veto a trade, never
    invent one, and never break a backtest that ran fine without it.
    """

    def __init__(self, config: "ExecutionConfig", df: pd.DataFrame):
        from app.integrations.jev_client import JevClient
        from app.services.jev_advisor import JevAdvisor

        self._config = config
        self._df = df
        self._symbol = str(df.attrs.get("symbol", "UNKNOWN"))
        self._interval = str(df.attrs.get("interval", ""))
        self._advisor = JevAdvisor(JevClient(offline=config.jev_offline))
        self._views: dict[int, object] = {}
        self.reviewed = 0
        self.vetoed = 0

    def _view(self, i: int):
        from app.integrations.jev_client import JevUnavailable

        if i not in self._views:
            try:
                self._views[i] = self._advisor.view(self._df, i, self._symbol, self._interval)
            except (JevUnavailable, Exception) as exc:  # noqa: BLE001 -- never break a backtest over the model
                logger.debug("Jev had no view for %s bar %s: %s", self._symbol, i, exc)
                self._views[i] = None
        return self._views[i]

    def review(self, i: int, signal: TradeDirection) -> TradeDirection | None:
        """The signal back if Jev agrees (or has no opinion), else None."""
        if self._config.jev_mode not in ("review", "both"):
            return signal
        view = self._view(i)
        if view is None:
            return signal
        self.reviewed += 1
        if self._advisor.approves(view, signal.value, self._config.jev_min_probability):
            return signal
        self.vetoed += 1
        return None

    def bracket(self, i: int, signal: TradeDirection, entry_price: float) -> tuple[float, float] | None:
        if self._config.jev_mode not in ("bracket", "both"):
            return None
        view = self._view(i)
        if view is None:
            return None
        from app.services.jev_advisor import _atr

        atr = _atr(self._df.iloc[: i + 1])
        stop, target = self._advisor.bracket(view, entry_price, atr, signal.value)
        if (signal == TradeDirection.LONG and not stop < entry_price < target) or (
            signal == TradeDirection.SHORT and not target < entry_price < stop
        ):
            return None  # a degenerate band is no bracket at all
        return stop, target


def _jev_gate(config: "ExecutionConfig", df: pd.DataFrame) -> "_JevGate | None":
    if getattr(config, "jev_mode", "off") == "off":
        return None
    return _JevGate(config, df)
