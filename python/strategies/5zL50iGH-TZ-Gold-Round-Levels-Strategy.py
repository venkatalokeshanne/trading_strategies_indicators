"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : TZ_Gold_Round_Levels_Strategy
Author       : TradZoo
Source URL   : https://www.tradingview.com/script/5zL50iGH-TZ-Gold-Round-Levels-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close, 15-minute charts only). Round numbers every `spacing` points: a bullish bar closing back above the level `offset` above a round number (previous close at or below it), with the
distance to the next round number minus the offset at least `Minimum final reward / risk` times the distance to the round number below, buys at the close with the stop at that round number and the target at the next one minus the offset
(sells mirrored). The bracket is issued with the entry and re-issued while the position is open.

Deviations from the original: use_bar_magnifier=true is not available (no intrabar data).
Not carried over: the round-level grid lines, labels and trade panel (display only). The original raises a runtime error on charts that are not 15 minutes or with an invalid offset; this port simply never trades there.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath


class TzGoldRoundLevels(Script):
    TITLE = "TZ_Gold_Round_Levels_Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=100000, default_qty_type="fixed", default_qty_value=1, commission_type="percent", commission_value=0, slippage=0,
                    margin_long=100, margin_short=100, process_orders_on_close=True)
    SOURCE = {"id": "5zL50iGH", "author": "TradZoo", "licence": "not stated",
              "url": "https://www.tradingview.com/script/5zL50iGH-TZ-Gold-Round-Levels-Strategy"}

    def init(self):
        self.spacing = self.input.float(50.0, "Round-number spacing", minval=0.01, group="Levels")
        self.offset = self.input.float(10.0, "Green / red offset", minval=0.01, group="Levels")
        self.min_final_rr = self.input.float(1.5, "Minimum final reward / risk", minval=1.5, step=0.1, group="Trade rules")
        self.trade_stop = NA
        self.trade_final = NA
        self.last_signal_bar = NA

    def on_bar(self):
        st = self.strategy
        close, open_ = self.close, self.open
        is15m = self.timeframe.isintraday and self.timeframe.multiplier == 15
        mintick = self.syminfo.mintick
        long_blue = pmath.round_to_mintick(pmath.floor(div(close - self.offset, self.spacing)) * self.spacing)
        long_green = pmath.round_to_mintick(long_blue + self.offset)
        long_final = pmath.round_to_mintick(long_blue + self.spacing - self.offset)
        long_risk = close - long_blue
        long_reward = long_final - close
        short_blue = pmath.round_to_mintick(pmath.ceil(div(close + self.offset, self.spacing)) * self.spacing)
        short_red = pmath.round_to_mintick(short_blue - self.offset)
        short_final = pmath.round_to_mintick(short_blue - self.spacing + self.offset)
        short_risk = short_blue - close
        short_reward = close - short_final
        tolerance = mintick * 0.000001
        close_1 = close[1]
        long_cross = (not na(close_1)) and close_1 <= long_green and close > long_green
        short_cross = (not na(close_1)) and close_1 >= short_red and close < short_red
        long_rr_ok = long_risk > 0 and long_reward > 0 and long_reward + tolerance >= self.min_final_rr * long_risk
        short_rr_ok = short_risk > 0 and short_reward > 0 and short_reward + tolerance >= self.min_final_rr * short_risk
        can_enter = is15m and self.barstate.isconfirmed and st.position_size == 0 and (na(self.last_signal_bar) or self.bar_index > self.last_signal_bar)
        buy_signal = can_enter and close > open_ and long_cross and long_rr_ok
        sell_signal = can_enter and close < open_ and short_cross and short_rr_ok
        if buy_signal:
            self.trade_stop = long_blue
            self.trade_final = long_final
            self.last_signal_bar = self.bar_index
            st.entry("Buy", st.long, comment="BUY")
            st.exit("Buy exit", from_entry="Buy", stop=self.trade_stop, limit=self.trade_final, comment_profit="FINAL TARGET", comment_loss="STOP LOSS")
        elif sell_signal:
            self.trade_stop = short_blue
            self.trade_final = short_final
            self.last_signal_bar = self.bar_index
            st.entry("Sell", st.short, comment="SELL")
            st.exit("Sell exit", from_entry="Sell", stop=self.trade_stop, limit=self.trade_final, comment_profit="FINAL TARGET", comment_loss="STOP LOSS")
        if st.position_size > 0:
            st.exit("Buy exit", from_entry="Buy", stop=self.trade_stop, limit=self.trade_final, comment_profit="FINAL TARGET", comment_loss="STOP LOSS")
        elif st.position_size < 0:
            st.exit("Sell exit", from_entry="Sell", stop=self.trade_stop, limit=self.trade_final, comment_profit="FINAL TARGET", comment_loss="STOP LOSS")
