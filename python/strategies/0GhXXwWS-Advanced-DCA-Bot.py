"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Advanced DCA Bot
Author       : fullmax
Source URL   : https://www.tradingview.com/script/0GhXXwWS-Advanced-DCA-Bot
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). An RSI crossing under the oversold level while flat opens the initial long of a fixed quantity. While long, each close at or below the last entry's close minus the drop percentage (up to the maximum number of steps) adds a long of base x multiplier^step;
the whole position is closed once the close reaches the take-profit percentage above the position's average price (read at the start of the bar).
Deviations from the original: none.
Not carried over: nothing (no display code in the source).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, pmath, ta


class AdvancedDcaBot(Script):
    TITLE = "Advanced DCA Bot"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=20)
    SOURCE = {"id": "0GhXXwWS", "author": "fullmax", "licence": "not stated", "url": "https://www.tradingview.com/script/0GhXXwWS-Advanced-DCA-Bot"}

    def init(self):
        i = self.input
        self.rsi_length = i.int(14, "RSI Length")
        self.rsi_oversold = i.int(30, "RSI Oversold Level")
        self.base_qty = i.int(100, "Start order qty in usdc-usdt", minval=1)
        self.dca_drop_pct = i.float(5.0, "Price Drop to Trigger DCA (%)", minval=0.1) / 100
        self.dca_multiplier = i.float(1.5, "DCA Multiplier (Size of next buy)", minval=1.0)
        self.max_dcas = i.int(5, "Maximum DCA Steps", minval=1)
        self.tp_pct = i.float(3.0, "Take Profit % from Average Price", minval=0.1) / 100
        self.last_entry_price = NA
        self.dca_count = 0
        self.current_base_qty = float(self.base_qty)

    def on_bar(self):
        st = self.strategy
        close = self.close
        rsi = ta.rsi(close, self.rsi_length)
        cross_under = ta.crossunder(rsi, self.rsi_oversold)
        avg_price = st.position_avg_price
        if cross_under and st.position_size == 0:
            st.entry("Initial_Entry", st.long, qty=self.current_base_qty)
            self.last_entry_price = float(close)
            self.dca_count = 0
        if st.position_size > 0 and self.dca_count < self.max_dcas:
            drop_threshold = self.last_entry_price * (1 - self.dca_drop_pct)
            if close <= drop_threshold:
                self.dca_count = self.dca_count + 1
                next_qty = self.current_base_qty * pmath.pow(self.dca_multiplier, self.dca_count)
                st.entry("DCA_" + str(self.dca_count), st.long, qty=next_qty)
                self.last_entry_price = float(close)
        if st.position_size > 0:
            tp_price = avg_price * (1 + self.tp_pct)
            if close >= tp_price:
                st.close_all(comment="Take Profit Hit")
                self.dca_count = 0
                self.last_entry_price = NA
