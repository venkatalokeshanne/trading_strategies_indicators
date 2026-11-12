"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Nifty 10-Candle ORB v4 (Alternating Trades)
Author       : Anupama
Source URL   : https://www.tradingview.com/script/cMy2aLGD-Nifty-10-Candle-ORB-v4-Alternating-Trades
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The first 10 (Number of Opening Candles) bars of each trading day (counted by candle_idx) give the opening range. After it and
before the last-entry hour, while flat, a close crossing over the range high goes long and under the range low goes short, but
never twice in the same direction in a row on one day (last_trade_type alternates). While a position is open at the close a
1 % target / 0.5 % stop around the average price is issued (it works from the next bar); from the exit time (15:15) every bar closes
any open position at the next open.

Deviations from the original: none.
Not carried over: the range plots (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, pmath, ta


class Nifty10CandleOrb(Script):
    TITLE = "Nifty 10-Candle ORB v4 (Alternating Trades)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000)
    SOURCE = {"id": "cMy2aLGD", "author": "Anupama", "licence": "not stated",
              "url": "https://www.tradingview.com/script/cMy2aLGD-Nifty-10-Candle-ORB-v4-Alternating-Trades"}

    def init(self):
        self.tp_percent = self.input.float(1.0, title="Profit Target (%)", step=0.1)
        self.sl_percent = self.input.float(0.5, title="Stop Loss (%)", step=0.1)
        self.num_candles = self.input.int(10, title="Number of Opening Candles", minval=1)
        self.exit_time_hour = self.input.int(15, title="Exit Hour (24h)", minval=0, maxval=23)
        self.exit_time_minute = self.input.int(15, title="Exit Minute", minval=0, maxval=59)
        self.last_trade_hour = self.input.int(15, title="Last Entry Hour (24h)", minval=0, maxval=23)
        self.session_high = NA
        self.session_low = NA
        self.candle_idx = 0
        self.last_trade_type = 0

    def on_bar(self):
        is_new_day = ta.change(self.time_fn("D")) != 0
        if is_new_day:
            self.session_high = NA
            self.session_low = NA
            self.candle_idx = 0
            self.last_trade_type = 0
        if (not na(self.time_fn("D"))) and self.candle_idx < self.num_candles:
            self.candle_idx = self.candle_idx + 1
            self.session_high = float(self.high) if na(self.session_high) else pmath.max(self.session_high, self.high)
            self.session_low = float(self.low) if na(self.session_low) else pmath.min(self.session_low, self.low)
        current_time = self.hour() * 100 + self.minute()
        is_exit_time = current_time >= (self.exit_time_hour * 100 + self.exit_time_minute)
        can_enter = current_time < (self.last_trade_hour * 100)
        st = self.strategy
        can_trade = self.candle_idx >= self.num_candles and st.position_size == 0 and can_enter and (not is_exit_time)
        cross_up = ta.crossover(self.close, self.session_high)
        cross_dn = ta.crossunder(self.close, self.session_low)
        long_condition = can_trade and cross_up and (self.last_trade_type <= 0)
        short_condition = can_trade and cross_dn and (self.last_trade_type >= 0)
        if long_condition:
            st.entry("Long", st.long)
            self.last_trade_type = 1
        if short_condition:
            st.entry("Short", st.short)
            self.last_trade_type = -1
        long_tp_price = st.position_avg_price * (1 + self.tp_percent / 100)
        long_sl_price = st.position_avg_price * (1 - self.sl_percent / 100)
        short_tp_price = st.position_avg_price * (1 - self.tp_percent / 100)
        short_sl_price = st.position_avg_price * (1 + self.sl_percent / 100)
        if st.position_size > 0:
            st.exit("Exit Long", "Long", limit=long_tp_price, stop=long_sl_price)
        if st.position_size < 0:
            st.exit("Exit Short", "Short", limit=short_tp_price, stop=short_sl_price)
        if is_exit_time:
            st.close_all(comment="EOD Square Off")
        self.plot(self.session_high if self.candle_idx >= self.num_candles else NA, color=color.green, linewidth=2, title="ORB High")
        self.plot(self.session_low if self.candle_idx >= self.num_candles else NA, color=color.red, linewidth=2, title="ORB Low")
