"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Market Open Break 2.0 (MNQ 09:30 Breakout v2)
Author       : Bnf6082
Source URL   : https://www.tradingview.com/script/7lMAaqyL-Market-Open-Break-2-0
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. The high / low of the 09:30 New York bar is the anchor; until 11:30 a close back through it (once per direction in a row, with the stop distance under `Max SL %`) enters with risk-based contracts, the target a percentage of the entry price and the stop the opposite anchor side. Per-day trade and loss counters and a skip after consecutive losing days are kept from the closed-trade list; any position is closed after 11:30.

Deviations from the original: none.
Not carried over: anchor lines, entry shapes and the performance table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath


class MarketOpenBreak20(Script):
    TITLE = "MNQ 09:30 Breakout v2"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=1, commission_type="cash_per_contract", commission_value=0.25, slippage=1, pyramiding=0)
    SOURCE = {"id": "7lMAaqyL", "author": "Bnf6082", "licence": "not stated",
              "url": "https://www.tradingview.com/script/7lMAaqyL-Market-Open-Break-2-0"}

    def init(self):
        i = self.input
        g = "Entry Rules"
        self.risk_per_trade = i.float(350.0, "Risk Per Trade ($)", group=g, minval=1, step=10)
        self.point_value = i.float(2.0, "Point Value ($)", group=g, minval=0.01, step=0.5)
        self.tp_pct = i.float(0.10, "TP %", group=g, minval=0.01, step=0.01)
        self.max_sl_pct = i.float(0.30, "Max SL %", group=g, minval=0.01, step=0.01)
        self.max_trades = i.int(3, "Max Trades/Day", group=g, minval=1, maxval=10)
        self.max_losses_day = i.int(2, "Max Losses/Day (CB)", group=g, minval=1, maxval=10)
        self.max_consec_days = i.int(2, "Max Consec Loss Days (CB)", group=g, minval=1, maxval=10)
        self.anchor_high = NA
        self.anchor_low = NA
        self.anchor_set = False
        self.trades_today = 0
        self.losses_today = 0
        self.skip_today = False
        self.last_direction = 0
        self.consec_loss = 0
        self.day_start_eq = 0.0
        self.prev_closed = 0

    def on_bar(self):
        st = self.strategy
        close = self.close
        ny_time = self.hour(self.time, "America/New_York") * 60 + self.minute(self.time, "America/New_York")
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
            self.skip_today = self.consec_loss >= self.max_consec_days
            if self.consec_loss >= self.max_consec_days:
                self.consec_loss = 0
            self.anchor_high = float(self.high)
            self.anchor_low = float(self.low)
            self.anchor_set = True
            self.trades_today = 0
            self.losses_today = 0
            self.last_direction = 0
            self.day_start_eq = st.netprofit
            self.prev_closed = st.closedtrades
        if st.closedtrades > self.prev_closed:
            for k in range(self.prev_closed, st.closedtrades):
                if st.closedtrades_profit(k) < 0:
                    self.losses_today += 1
            self.prev_closed = st.closedtrades
        day_ok = self.anchor_set and (not self.skip_today) and self.trades_today < self.max_trades and self.losses_today < self.max_losses_day
        can_trade = day_ok and st.position_size == 0 and in_window
        close_1 = close[1]
        break_above = (not na(self.anchor_high)) and close > self.anchor_high and close_1 <= self.anchor_high
        break_below = (not na(self.anchor_low)) and close < self.anchor_low and close_1 >= self.anchor_low
        if can_trade and break_above and self.last_direction != 1:
            sl_pct = div(close - self.anchor_low, close) * 100
            if sl_pct <= self.max_sl_pct:
                sl_points = close - self.anchor_low
                qty = pmath.max(1, pmath.floor(div(self.risk_per_trade, sl_points * self.point_value)))
                tp_price = close * (1.0 + self.tp_pct / 100.0)
                self.trades_today += 1
                self.last_direction = 1
                st.entry("Long", st.long, qty=qty)
                st.exit("Long Exit", from_entry="Long", limit=tp_price, stop=self.anchor_low)
        if can_trade and break_below and self.last_direction != -1:
            sl_pct = div(self.anchor_high - close, close) * 100
            if sl_pct <= self.max_sl_pct:
                sl_points = self.anchor_high - close
                qty = pmath.max(1, pmath.floor(div(self.risk_per_trade, sl_points * self.point_value)))
                tp_price = close * (1.0 - self.tp_pct / 100.0)
                self.trades_today += 1
                self.last_direction = -1
                st.entry("Short", st.short, qty=qty)
                st.exit("Short Exit", from_entry="Short", limit=tp_price, stop=self.anchor_high)
        if past_window and st.position_size != 0:
            st.close_all(comment="Time Stop")
