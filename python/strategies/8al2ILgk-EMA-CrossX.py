"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA CrossX
Author       : ayusattv
Source URL   : https://www.tradingview.com/script/8al2ILgk-EMA-CrossX
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. `crossHappened[waitBars]` is the bullish EMA cross from `waitBars` bars ago (bool
history through H(), na before the start is false). While long, the exit is re-issued every bar: with the
trailing option a stop at entry - 2.5 plus a trailing stop that is active from the entry price (trail_points
= 0) and follows at 1.0 point; otherwise a fixed stop and 4-point target. It first works on the bar after
the fill.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, ta, truthy


class EmaCrossX(Script):
    TITLE = "EMA CrossX"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, default_qty_type="fixed", default_qty_value=1)
    SOURCE = {"id": "8al2ILgk", "author": "ayusattv", "licence": "not stated",
              "url": "https://www.tradingview.com/script/8al2ILgk-EMA-CrossX"}

    def init(self):
        self.fast_len = self.input.int(9, "Fast EMA Length")
        self.slow_len = self.input.int(19, "Slow EMA Length")
        self.wait_bars = self.input.int(2, "Entry Delay (Candles)", minval=0)
        self.take_profit_points = self.input.float(4.0, "Take Profit (Points)")
        self.stop_loss_points = self.input.float(2.5, "Stop Loss (Points)")
        self.use_trailing = self.input.bool(True, "Enable Trailing Stop (Overrides Fixed TP)?")
        self.trailing_dist_pts = self.input.float(1.0, "Trailing Distance (Points)")

    def on_bar(self):
        ema_fast = ta.ema(self.close, self.fast_len)
        ema_slow = ta.ema(self.close, self.slow_len)
        self.plot(ema_fast, color=color.blue, title="EMA Fast")
        self.plot(ema_slow, color=color.orange, title="EMA Slow")
        cross_happened = ta.crossover(ema_fast, ema_slow)
        self.H("cross").set(1.0 if cross_happened else 0.0)
        enter_long = truthy(self.H("cross")[self.wait_bars])
        st = self.strategy
        if enter_long:
            st.entry("Long", st.long)
        if st.position_size > 0:
            entry_price = st.position_avg_price
            sl_level = entry_price - self.stop_loss_points
            tp_level = entry_price + self.take_profit_points
            if self.use_trailing:
                trail_offset_ticks = div(self.trailing_dist_pts, self.syminfo.mintick)
                st.exit("Exit Trail", "Long", stop=sl_level, trail_points=0, trail_offset=trail_offset_ticks)
            else:
                st.exit("Exit Fixed", "Long", stop=sl_level, limit=tp_level)
        self.plotshape(cross_happened, title="Cross")
        self.plotshape(enter_long, title="Buy")
