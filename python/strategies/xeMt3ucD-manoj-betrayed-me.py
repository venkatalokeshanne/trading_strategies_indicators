"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : manoj betrayed me
Author       : vasudevshenoy
Source URL   : https://www.tradingview.com/script/xeMt3ucD-manoj-betrayed-me
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). A close beyond the smoothed (RMA) high / low followed by a bar that also holds its low above the smoothed high (high below the smoothed low) is the confirmation; a stop entry at that bar's high (low) is placed with a stop at the previous smoothed low (high) and a target of a multiple of the confirmation bar's range. The pending entry lives for one bar; everything is cancelled and closed on the last bar of the session and outside it.

Deviations from the original: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


class ManojBetrayedMe(Script):
    TITLE = "manoj betrayed me"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "xeMt3ucD", "author": "vasudevshenoy", "licence": "not stated",
              "url": "https://www.tradingview.com/script/xeMt3ucD-manoj-betrayed-me"}

    def init(self):
        self.len = self.input.int(20, "SMMA Length", minval=1)
        self.target_mult = self.input.float(2.0, "Target Multiplier", minval=0.1)
        self.trade_session = self.input.session("0915-1530", "Trading Session")
        self.pending_dir = 0
        self.pending_bar = NA

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        in_session = not na(self.time_fn(None, self.trade_session))
        bar_close_hour = self.hour(self.time_close, self.syminfo.timezone)
        bar_close_minute = self.minute(self.time_close, self.syminfo.timezone)
        is_session_close_bar = in_session and (bar_close_hour > 15 or (bar_close_hour == 15 and bar_close_minute >= 30))
        can_trade = in_session and not is_session_close_bar
        smma_high = ta.rma(high, self.len)
        smma_low = ta.rma(low, self.len)
        sh_h, sl_h, bs_h, ss_h = self.H("smma_high"), self.H("smma_low"), self.H("buy_signal"), self.H("sell_signal")
        smma_low_1 = sl_h[1]
        smma_high_1 = sh_h[1]
        buy_signal_1, sell_signal_1 = bs_h[1], ss_h[1]
        buy_signal = can_trade and close > smma_high
        sell_signal = can_trade and close < smma_low
        sh_h.set(smma_high)
        sl_h.set(smma_low)
        bs_h.set(buy_signal)
        ss_h.set(sell_signal)
        buy_confirm = can_trade and (not na(buy_signal_1)) and bool(buy_signal_1) and close > smma_high and low > smma_high
        sell_confirm = can_trade and (not na(sell_signal_1)) and bool(sell_signal_1) and close < smma_low and high < smma_low
        if is_session_close_bar:
            st.cancel("Buy")
            st.cancel("Sell")
            st.close_all(comment="Session Close")
            self.pending_dir = 0
            self.pending_bar = NA
        if not in_session:
            st.cancel("Buy")
            st.cancel("Sell")
            self.pending_dir = 0
            self.pending_bar = NA
        if self.pending_dir != 0 and self.bar_index == self.pending_bar + 1 and st.position_size == 0:
            st.cancel("Buy" if self.pending_dir == 1 else "Sell")
            self.pending_dir = 0
            self.pending_bar = NA
        if st.position_size != 0:
            self.pending_dir = 0
            self.pending_bar = NA
        if buy_confirm and st.position_size == 0:
            confirmation_high = high
            confirmation_size = high - low
            buy_entry = confirmation_high
            buy_stop = smma_low_1
            buy_target = confirmation_high + self.target_mult * confirmation_size
            st.cancel("Sell")
            st.entry("Buy", st.long, stop=buy_entry)
            st.exit("Buy Exit", "Buy", stop=buy_stop, limit=buy_target)
            self.pending_dir = 1
            self.pending_bar = self.bar_index
        if sell_confirm and st.position_size == 0:
            confirmation_low = low
            confirmation_size = high - low
            sell_entry = confirmation_low
            sell_stop = smma_high_1
            sell_target = confirmation_low - self.target_mult * confirmation_size
            st.cancel("Buy")
            st.entry("Sell", st.short, stop=sell_entry)
            st.exit("Sell Exit", "Sell", stop=sell_stop, limit=sell_target)
            self.pending_dir = -1
            self.pending_bar = self.bar_index
