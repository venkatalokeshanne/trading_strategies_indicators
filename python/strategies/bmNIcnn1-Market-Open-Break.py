"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : MNQ 09:30 Breakout
Author       : Bnf6082
Source URL   : https://www.tradingview.com/script/bmNIcnn1-Market-Open-Break
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. The 09:30 New York bar's high / low are the anchors. Until 11:30 a close breaking out of the anchor (with the previous close on the other side) enters at the next open, provided the stop (the opposite anchor) is within `Max SL %` of the close, alternating
directions, at most `Max Trades/Day`. Stop = the opposite anchor, target = `TP %` of the close, both placed with the entry. After 11:30 any position is closed. Two losing days in a row skip the next day.

Deviations from the original: none.
Not carried over: the anchor lines, signal markers and the performance table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na

NY = "America/New_York"


class MarketOpenBreak(Script):
    TITLE = "MNQ 09:30 Breakout"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=1, commission_type="cash_per_contract", commission_value=0.25, slippage=1, pyramiding=0)
    SOURCE = {"id": "bmNIcnn1", "author": "Bnf6082", "licence": "not stated",
              "url": "https://www.tradingview.com/script/bmNIcnn1-Market-Open-Break"}

    def init(self):
        g = "Entry Rules"
        self.contracts = self.input.int(1, "Contracts", group=g, minval=1)
        self.tp_pct = self.input.float(0.10, "TP %", group=g, minval=0.01, step=0.01)
        self.max_sl_pct = self.input.float(0.30, "Max SL %", group=g, minval=0.01, step=0.01)
        self.max_trades = self.input.int(3, "Max Trades/Day", group=g, minval=1, maxval=10)
        self.anchor_high = NA
        self.anchor_low = NA
        self.anchor_set = False
        self.trades_today = 0
        self.skip_today = False
        self.last_direction = 0
        self.consec_loss = 0
        self.day_start_eq = 0.0

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        ny_time = self.hour(self.time, NY) * 60 + self.minute(self.time, NY)
        at_anchor = ny_time == 9 * 60 + 30
        in_window = ny_time >= 9 * 60 + 31 and ny_time <= 11 * 60 + 30
        past_window = ny_time > 11 * 60 + 30
        if at_anchor:
            if self.anchor_set:
                day_pnl = st.netprofit - self.day_start_eq
                if day_pnl < 0:
                    self.consec_loss += 1
                else:
                    self.consec_loss = 0
            self.skip_today = self.consec_loss >= 2
            if self.consec_loss >= 2:
                self.consec_loss = 0
            self.anchor_high = float(high)
            self.anchor_low = float(low)
            self.anchor_set = True
            self.trades_today = 0
            self.last_direction = 0
            self.day_start_eq = st.netprofit
        day_ok = self.anchor_set and (not self.skip_today) and self.trades_today < self.max_trades
        can_trade = day_ok and st.position_size == 0 and in_window
        close_1 = close[1]
        break_above = (not na(self.anchor_high)) and close > self.anchor_high and close_1 <= self.anchor_high
        break_below = (not na(self.anchor_low)) and close < self.anchor_low and close_1 >= self.anchor_low
        if can_trade and break_above and self.last_direction != 1:
            sl_pct = div(close - self.anchor_low, close) * 100
            if sl_pct <= self.max_sl_pct:
                self.trades_today += 1
                self.last_direction = 1
                tp_price = close * (1.0 + self.tp_pct / 100.0)
                st.entry("Long", st.long, qty=self.contracts)
                st.exit("Long Exit", from_entry="Long", limit=tp_price, stop=self.anchor_low)
        if can_trade and break_below and self.last_direction != -1:
            sl_pct = div(self.anchor_high - close, close) * 100
            if sl_pct <= self.max_sl_pct:
                self.trades_today += 1
                self.last_direction = -1
                tp_price = close * (1.0 - self.tp_pct / 100.0)
                st.entry("Short", st.short, qty=self.contracts)
                st.exit("Short Exit", from_entry="Short", limit=tp_price, stop=self.anchor_high)
        if past_window and st.position_size != 0:
            st.close_all(comment="Time Stop")
