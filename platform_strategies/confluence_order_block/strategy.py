"""
Confluence Order Block.

Trades order-block zones confirmed by a 4-component confluence score
(ATR displacement, percent displacement, volume pivot, structure
alignment). Zone detection and lifecycle -- activation, mitigation,
expiry, and first-touch consumption -- live in
app.indicators.confluence_order_block and are reused as-is.

This file overrides Strategy.run() instead of the usual
generate_entries/generate_exits + simulate_trades path because the
validated execution model can't be expressed as a plain signal series:
    - entry fills at a LIMIT price at the zone's proximal edge (a gap
      through the zone fills at the bar's open instead), not at close.
    - the stop is anchored to the zone's edge offset by stop_buf x the
      ATR at the order-block candle's FORMATION bar, not the ATR at
      entry time -- a zone can be entered up to max_age bars after it
      formed.
    - position sizing is 100% of current equity (compounding), not a
      fixed quantity or a %-risk sizing rule.

Because of this, Execution Settings' generic risk-management fields
(stop_loss_*, take_profit_*, risk_per_trade_pct, max_position_value_pct,
quantity, force_close_at_session_end) have NO effect on this strategy --
only capital, slippage_pct, and commission_per_trade are honored. This
strategy brings its own validated risk model instead, which is exactly
the case Strategy.run()'s docstring anticipates a strategy overriding
"the whole lifecycle" for.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, Trade, TradeDirection
from app.indicators.confluence_order_block import ConfluenceOrderBlock as ConfluenceOrderBlockIndicator
from app.indicators.ema import EMA
from app.strategies.registry import strategy_registry


def _trend_allows(close: float, ema_value: float | None, direction: int, trend_len: int) -> bool:
    # trend_len == 0 disables the filter; a not-yet-warmed-up EMA (NaN)
    # is treated the same way rather than blocking every early entry.
    if trend_len <= 0 or ema_value is None or pd.isna(ema_value):
        return True
    return close > ema_value if direction == 1 else close < ema_value


@strategy_registry.register("confluence_order_block")
class ConfluenceOrderBlock(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="confluence_order_block",
            display_name="Confluence Order Block",
            description=(
                "Order-block zones confirmed by a 4-of-4 confluence score (ATR "
                "displacement, percent displacement, volume pivot, structure "
                "alignment); entries are limit fills at the zone's proximal edge "
                "with a stop anchored to the zone's formation-bar ATR and a fixed "
                "reward:risk target. Validated on 30-minute bars -- for 5-minute "
                "bars use disp_atr=1.2, disp_pct=0.4, max_age=30."
            ),
            category="price_action",
            indicators_used=["confluence_order_block", "ema"],
            default_params={
                "atr_len": 14,
                "impulse_bars": 5,
                "disp_atr": 2.0,
                "disp_pct": 1.0,
                "vol_len": 5,
                "os_len": 5,
                "min_score": 3,
                "zone_width": "half",
                "mitigation": "close",
                "max_age": 60,
                "stop_buf": 0.5,
                "rr": 1.5,
                "trend_len": 100,
                "allow_short": True,
            },
            live_caution=(
                "An order block only becomes valid once price has already displaced away from it, so "
                "the zone is confirmed well after the fact -- entries are trading a level whose window "
                "has partly already passed, and the limit-fill assumption at its proximal edge is harder "
                "to replicate live than in a backtest."
            ),
            entry_conditions=[
                "A demand/supply zone forms when an order-block candle's impulse leg "
                "scores >= min_score of 4: ATR displacement, percent displacement, a "
                "volume pivot on the OB candle, and structure (swing) alignment.",
                "Entry triggers on the zone's first touch -- a later retest of the "
                "same zone is not tradeable, it was already consumed.",
                "Long only if close > EMA(trend_len); short only if close < "
                "EMA(trend_len) and allow_short is true (trend_len=0 disables the filter).",
                "Fill is a limit order at the zone's proximal edge; a gap through the "
                "zone fills at the bar's open instead.",
            ],
            exit_conditions=[
                "Stop = zone's far edge offset by stop_buf x ATR-at-formation; "
                "target = entry + rr x initial risk.",
                "If a single bar's range spans both, the stop is assumed to have "
                "filled first.",
                "Any position still open at the end of the data is closed at the "
                "last bar's close.",
            ],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = ConfluenceOrderBlockIndicator().calculate(
            df,
            {
                "atr_len": p["atr_len"],
                "impulse_bars": p["impulse_bars"],
                "disp_atr": p["disp_atr"],
                "disp_pct": p["disp_pct"],
                "vol_len": p["vol_len"],
                "os_len": p["os_len"],
                "min_score": p["min_score"],
                "zone_width": p["zone_width"],
                "mitigation": p["mitigation"],
                "max_age": p["max_age"],
            },
        )
        if p["trend_len"] > 0:
            out = EMA().calculate(out, {"period": p["trend_len"]})
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        """Best-effort signal view for UI/introspection only -- see the
        module docstring. Actual trade generation happens in run(), which
        needs per-zone stop/target/fill data this series can't carry.
        """
        p = self.validate_params(params)
        ema_col = f"ema_{p['trend_len']}" if p["trend_len"] > 0 else None
        entries = pd.Series(None, index=df.index, dtype=object)
        for i in range(len(df)):
            sig = df["cob_signal"].iloc[i]
            if sig is None:
                continue
            direction = 1 if sig == "long" else -1
            if direction == -1 and not p["allow_short"]:
                continue
            ema_value = df[ema_col].iloc[i] if ema_col else None
            if not _trend_allows(df["close"].iloc[i], ema_value, direction, p["trend_len"]):
                continue
            entries.iloc[i] = TradeDirection.LONG if direction == 1 else TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        """Not used by run() -- exits here are per-trade stop/target levels
        derived at entry time, not a bar-level condition expressible as a
        plain boolean series.
        """
        self.validate_params(params)
        return pd.Series(False, index=df.index)

    def run(
        self,
        df: pd.DataFrame,
        params: dict[str, Any],
        execution_config: "ExecutionConfig | None" = None,
    ) -> list[Trade]:
        from app.strategies.execution import ExecutionConfig

        p = self.validate_params(params)
        config = execution_config or ExecutionConfig()
        enriched = self.prepare(df, params)

        ema_col = f"ema_{p['trend_len']}" if p["trend_len"] > 0 else None
        signal = enriched["cob_signal"]
        zone_top = enriched["cob_zone_top"]
        zone_bottom = enriched["cob_zone_bottom"]
        atr_at_formation = enriched["cob_atr_at_formation"]
        open_ = enriched["open"]
        high = enriched["high"]
        low = enriched["low"]
        close = enriched["close"]
        index = enriched.index
        n = len(enriched)

        slippage = config.slippage_pct
        commission = config.commission_per_trade
        stop_buf = p["stop_buf"]
        rr = p["rr"]
        allow_short = p["allow_short"]
        trend_len = p["trend_len"]

        equity = config.capital
        trades: list[Trade] = []

        open_direction: int | None = None
        open_entry_index: int | None = None
        open_entry_time = None
        open_entry_price: float | None = None
        open_stop: float | None = None
        open_target: float | None = None
        open_shares: float | None = None

        for i in range(n):
            ts = index[i]

            # --- manage an already-open position (checked from the bar
            # after entry onward -- never on the entry bar itself).
            if open_direction is not None and i > open_entry_index:
                bar_low = low.iloc[i]
                bar_high = high.iloc[i]
                bar_open = open_.iloc[i]
                exit_price = None
                exit_reason = None

                # Stop checked before target -- the opposite is a common
                # and flattering error when a single bar spans both.
                if open_direction == 1:
                    if bar_low <= open_stop:
                        exit_price = min(open_stop, bar_open)
                        exit_reason = "stop_loss"
                    elif bar_high >= open_target:
                        exit_price = max(open_target, bar_open)
                        exit_reason = "take_profit"
                else:
                    if bar_high >= open_stop:
                        exit_price = max(open_stop, bar_open)
                        exit_reason = "stop_loss"
                    elif bar_low <= open_target:
                        exit_price = min(open_target, bar_open)
                        exit_reason = "take_profit"

                if exit_price is not None:
                    exit_price = exit_price * (1 - slippage * open_direction)
                    pnl = (exit_price - open_entry_price) * open_direction * open_shares - commission
                    equity += pnl
                    trades.append(
                        Trade(
                            entry_time=open_entry_time,
                            exit_time=ts,
                            direction=TradeDirection.LONG if open_direction == 1 else TradeDirection.SHORT,
                            entry_price=open_entry_price,
                            exit_price=exit_price,
                            quantity=open_shares,
                            pnl=pnl,
                            exit_reason=exit_reason,
                        )
                    )
                    open_direction = None
                    open_entry_index = None
                    open_entry_time = None
                    open_entry_price = None
                    open_stop = None
                    open_target = None
                    open_shares = None
                    # A zone consumed on this same bar is not entered --
                    # matches simulate_trades' convention of never
                    # re-entering on the bar a position just closed.
                    continue

            # --- attempt a new entry (one position at a time).
            if open_direction is None:
                sig = signal.iloc[i]
                if sig is None:
                    continue

                direction = 1 if sig == "long" else -1
                if direction == -1 and not allow_short:
                    continue

                ema_value = enriched[ema_col].iloc[i] if ema_col else None
                if not _trend_allows(close.iloc[i], ema_value, direction, trend_len):
                    continue

                z_top = zone_top.iloc[i]
                z_bottom = zone_bottom.iloc[i]
                z_atr = atr_at_formation.iloc[i]
                bar_open = open_.iloc[i]

                # Resting limit at the proximal edge; a gap through it
                # fills at the open instead.
                fill = min(bar_open, z_top) if direction == 1 else max(bar_open, z_bottom)
                entry_price = fill * (1 + slippage * direction)

                stop = z_bottom - stop_buf * z_atr if direction == 1 else z_top + stop_buf * z_atr
                risk = (entry_price - stop) * direction
                if risk <= 0:
                    continue
                target = entry_price + direction * rr * risk
                shares = equity / entry_price if entry_price > 0 else 0.0
                if shares <= 0:
                    continue

                open_direction = direction
                open_entry_index = i
                open_entry_time = ts
                open_entry_price = entry_price
                open_stop = stop
                open_target = target
                open_shares = shares

        # Any position still open at the end of the data: force-close at
        # the last bar's close.
        if open_direction is not None:
            last_price = close.iloc[-1]
            exit_price = last_price * (1 - slippage * open_direction)
            pnl = (exit_price - open_entry_price) * open_direction * open_shares - commission
            trades.append(
                Trade(
                    entry_time=open_entry_time,
                    exit_time=index[-1],
                    direction=TradeDirection.LONG if open_direction == 1 else TradeDirection.SHORT,
                    entry_price=open_entry_price,
                    exit_price=exit_price,
                    quantity=open_shares,
                    pnl=pnl,
                    exit_reason="end_of_data",
                )
            )

        return trades
