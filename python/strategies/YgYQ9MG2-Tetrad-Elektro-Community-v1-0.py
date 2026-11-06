"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Tetrad Elektro Community v1.0
Author       : TetradProtocol
Source URL   : https://www.tradingview.com/script/YgYQ9MG2-Tetrad-Elektro-Community-v1-0
Pine version : v6
Licence      : MPL-2.0
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A close at or under the wide lower Bollinger band with both RSIs depressed enters long; a close at or over the upper band with the RSIs elevated, or a price new high not confirmed by the RSI or the MACD line, enters short. The long exits when the upper-band condition holds and the short when the close is under the lower band or both RSIs are low; an optional stop (a factor of the average price, working from the bar after the fill) and an optional time stop are available.

Deviations from the original: none.
Not carried over: band plots, fills, signal shapes, position labels and the branding table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


class TetradElektro(Script):
    TITLE = "Tetrad Elektro Community v1.0"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100, commission_type="percent", commission_value=0.05, slippage=3, default_qty_type="percent_of_equity",
                    default_qty_value=100, pyramiding=0)
    SOURCE = {"id": "YgYQ9MG2", "author": "TetradProtocol", "licence": "MPL-2.0",
              "url": "https://www.tradingview.com/script/YgYQ9MG2-Tetrad-Elektro-Community-v1-0"}

    def init(self):
        i = self.input
        g = "Mode"
        self.trade_mode = i.string("Long & Short", "Trade Mode", options=["Long & Short", "Long Only", "Short Only"], group=g)
        self.flat_first = i.bool(True, "Require Flat Before New Opposite Entry?", group=g)
        g = "Bollinger Bands"
        self.bb_length = i.int(265, "Bollinger Length", minval=1, group=g)
        self.bb_mult = i.float(3.3, "Bollinger Multiplier", step=0.1, group=g)
        g = "RSI Filters"
        self.rsi_len_main = i.int(14, "Main RSI Length", minval=1, group=g)
        self.rsi_len_fast = i.int(7, "Fast RSI Length", minval=1, group=g)
        self.long_main = i.float(23.0, "Long Entry Main RSI ≤", step=0.1, group=g)
        self.long_fast = i.float(85.0, "Long Entry Fast RSI ≤", step=0.1, group=g)
        self.exit_long_main = i.float(77.0, "Long Exit / Short Setup Main RSI ≥", step=0.1, group=g)
        self.exit_short_fast = i.float(23.0, "Short Exit Fast RSI ≤", step=0.1, group=g)
        g = "MACD Divergence"
        self.fast_len = i.int(12, "MACD Fast Length", minval=1, group=g)
        self.slow_len = i.int(26, "MACD Slow Length", minval=1, group=g)
        self.signal_len = i.int(14, "MACD Signal Length", minval=1, group=g)
        self.div_lookback = i.int(20, "Divergence Lookback Bars", minval=1, group=g)
        self.use_bear_div = i.bool(True, "Enable Bearish Divergence Short Setup?", group=g)
        g = "Risk Management"
        self.use_stop = i.bool(False, "Use Stop Loss?", group=g)
        self.long_stop_factor = i.float(0.85, "Long Stop Factor", step=0.01, group=g)
        self.short_stop_factor = i.float(1.09, "Short Stop Factor", step=0.01, group=g)
        self.use_time_stop = i.bool(False, "Use Time-Based Stop?", group=g)
        self.time_stop_days = i.int(2, "Time Stop Days", minval=1, group=g)
        self.entry_time = NA

    def on_bar(self):
        st = self.strategy
        close = self.close
        basis = ta.sma(close, self.bb_length)
        dev = self.bb_mult * ta.stdev(close, self.bb_length)
        upper = basis + dev
        lower = basis - dev
        rsi_main = ta.rsi(close, self.rsi_len_main)
        rsi_fast = ta.rsi(close, self.rsi_len_fast)
        macd_line = ta.ema(close, self.fast_len) - ta.ema(close, self.slow_len)
        rsi_h, macd_h = self.H("rsi_main"), self.H("macd_line")
        price_new_high = close > ta.highest(close[1], self.div_lookback)
        rsi_not_conf = rsi_main < ta.highest(rsi_h[1], self.div_lookback)
        macd_not_conf = macd_line < ta.highest(macd_h[1], self.div_lookback)
        rsi_h.set(rsi_main)
        macd_h.set(macd_line)
        bearish_div = self.use_bear_div and price_new_high and (rsi_not_conf or macd_not_conf)
        buy_condition = close <= lower and rsi_main <= self.long_main and rsi_fast <= self.long_fast
        sell_condition = close >= upper and rsi_main >= self.exit_long_main and rsi_fast >= self.exit_short_fast
        short_setup_bb = close >= upper and rsi_main >= self.exit_long_main and rsi_fast >= self.exit_short_fast
        short_condition = short_setup_bb or bearish_div
        short_exit_condition = close <= lower or (rsi_main <= self.long_main and rsi_fast <= self.exit_short_fast)
        allow_long = self.trade_mode == "Long & Short" or self.trade_mode == "Long Only"
        allow_short = self.trade_mode == "Long & Short" or self.trade_mode == "Short Only"
        is_flat = st.position_size == 0
        is_long = st.position_size > 0
        is_short = st.position_size < 0
        can_open_long = allow_long and buy_condition and (is_flat if self.flat_first else not is_long)
        can_open_short = allow_short and short_condition and (is_flat if self.flat_first else not is_short)
        pos_h = self.H("pos")
        pos_prev = pos_h[1]
        pos_h.set(st.position_size)
        new_position_opened = st.position_size != 0 and pos_prev == 0
        position_closed = st.position_size == 0 and pos_prev != 0
        if new_position_opened:
            self.entry_time = float(self.time)
        if position_closed:
            self.entry_time = NA
        if can_open_long:
            st.entry("Long", st.long)
        if can_open_short:
            st.entry("Short", st.short)
        if is_long:
            long_stop_price = st.position_avg_price * self.long_stop_factor
            if self.use_stop:
                st.exit("Long Stop", from_entry="Long", stop=long_stop_price)
            if sell_condition:
                st.close("Long", comment="Long Exit")
        if is_short:
            short_stop_price = st.position_avg_price * self.short_stop_factor
            if self.use_stop:
                st.exit("Short Stop", from_entry="Short", stop=short_stop_price)
            if short_exit_condition:
                st.close("Short", comment="Short Exit")
        if self.use_time_stop and st.position_size != 0 and not na(self.entry_time):
            ms_since_entry = self.time - self.entry_time
            days_since_entry = ms_since_entry / 86400000.0
            if days_since_entry >= self.time_stop_days:
                st.close_all(comment="Time Stop")
