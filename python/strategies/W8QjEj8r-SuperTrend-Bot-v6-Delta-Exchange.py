"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SuperTrend Bot v6 — Delta Exchange
Author       : kapsystem
Source URL   : https://www.tradingview.com/script/W8QjEj8r-SuperTrend-Bot-v6-Delta-Exchange
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A SuperTrend(10, 3) flip to up buys `qty` contracts, a flip to down sells short (reversing); no stops.

Deviations from the original: none.
Not carried over: the line plots, BUY / SELL labels, bar colouring and alertcondition (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, ta


class SupertrendBotV6(Script):
    TITLE = "SuperTrend Bot v6 — Delta Exchange"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=1, initial_capital=100000, commission_type="percent",
                    commission_value=0.05, pyramiding=0)
    SOURCE = {"id": "W8QjEj8r", "author": "kapsystem", "licence": "not stated",
              "url": "https://www.tradingview.com/script/W8QjEj8r-SuperTrend-Bot-v6-Delta-Exchange"}

    def init(self):
        self.atr_len = self.input.int(10, "ATR Length", minval=1, group="SuperTrend Settings")
        self.factor = self.input.float(3.0, "Factor (Multiplier)", minval=0.1, step=0.1, group="SuperTrend Settings")
        self.qty = self.input.int(1, "Order Quantity (Contracts)", minval=1, group="Order Settings")

    def on_bar(self):
        supertrend, direction = ta.supertrend(self.factor, self.atr_len)
        dir_h = self.H("dir")
        prev_dir = dir_h[1]
        dir_h.set(direction)
        is_bullish = direction == -1
        is_bearish = direction == 1
        buy_signal = is_bullish and prev_dir == 1
        sell_signal = is_bearish and prev_dir == -1
        st = self.strategy
        if buy_signal:
            st.entry("Long", st.long, qty=self.qty)
        if sell_signal:
            st.entry("Short", st.short, qty=self.qty)
        self.plot(supertrend if is_bullish else NA, title="Uptrend Line", color=color.green, linewidth=2)
        self.plot(supertrend if is_bearish else NA, title="Downtrend Line", color=color.red, linewidth=2)
