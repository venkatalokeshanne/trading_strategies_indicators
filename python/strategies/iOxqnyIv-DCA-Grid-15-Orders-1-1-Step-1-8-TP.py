"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : DCA Grid 15 Orders - 1.1% Step - 1.8% TP
Author       : Tijara123
Source URL   : https://www.tradingview.com/script/iOxqnyIv-DCA-Grid-15-Orders-1-1-Step-1-8-TP
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Statement order matters here and is kept: when the position has just closed,
the "flat" block (re-arms orderCount = 1) runs first and the "just closed" block at the end then resets
orderCount to 0 and lastEntryPrice to na, so after the first cycle the grid never adds again (the added
orders need lastEntryPrice, which stays na). That is what the Pine source does. `strategy.position_size[1]`
is the position at the previous bar's close (history through H()). strategy.exit("TP", limit=...) has no
from_entry, so it closes every open entry at the average-price target issued on the previous bar.

Deviations from the original: none.
Not carried over: the average-price and take-profit plots keep their values; nothing dropped.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, pmath


class DcaGrid15Orders(Script):
    TITLE = "DCA Grid 15 Orders - 1.1% Step - 1.8% TP"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(pyramiding=15, initial_capital=10000, default_qty_type="cash", default_qty_value=100)
    SOURCE = {"id": "iOxqnyIv", "author": "Tijara123", "licence": "not stated",
              "url": "https://www.tradingview.com/script/iOxqnyIv-DCA-Grid-15-Orders-1-1-Step-1-8-TP"}

    def init(self):
        self.base_order = self.input.float(100, "Base Order Size ($)")
        self.grid_step = self.input.float(1.1, "Grid Step (%)")
        self.take_profit = self.input.float(1.8, "Take Profit (%)")
        self.multiplier = self.input.float(1.2, "Size Multiplier")
        self.max_orders = self.input.int(15, "Max Orders")
        self.order_count = 0
        self.last_entry_price = NA

    def on_bar(self):
        st = self.strategy
        prev_pos = self.H("pos")[1]                              # strategy.position_size[1]
        if st.position_size == 0:
            st.entry("Long_1", st.long, qty=div(self.base_order, self.close))
            self.order_count = 1
            self.last_entry_price = float(self.close)
        if st.position_size > 0 and self.order_count < self.max_orders:
            next_buy_price = self.last_entry_price * (1 - self.grid_step / 100)
            if self.low <= next_buy_price:
                order_qty_cash = self.base_order * pmath.pow(self.multiplier, self.order_count)
                st.entry(f"Long_{self.order_count + 1}", st.long, qty=div(order_qty_cash, self.close))
                self.last_entry_price = next_buy_price
                self.order_count += 1
        avg_price = st.position_avg_price
        tp_price = avg_price * (1 + self.take_profit / 100)
        if st.position_size > 0:
            st.exit("TP", limit=tp_price)
        if st.position_size == 0 and prev_pos > 0:
            self.order_count = 0
            self.last_entry_price = NA
        self.H("pos").set(st.position_size)
        self.plot(avg_price if st.position_size > 0 else NA, color=color.yellow, linewidth=2, title="Average Price")
        self.plot(tp_price if st.position_size > 0 else NA, color=color.green, linewidth=2, title="Take Profit")
