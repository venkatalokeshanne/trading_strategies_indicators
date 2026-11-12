"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA & Fib Confluence with 3 Targets + Trailing v6
Author       : alanshospitality
Source URL   : https://www.tradingview.com/script/diZ8Oes6-EMA-Fib-Confluence-with-3-Targets-Trailing-v6
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A fast EMA above (below) the slow EMA with the close crossing over the 61.8 % retracement from the 50-bar high (under the retracement from the 50-bar low) while the script's position tracker is flat enters long (short) and sets three
targets, a trailing stop level and the tracker to long (short).
Quirk kept: the last statement of the script resets the tracker to 0 whenever strategy.position_size is 0 - which is the case on the signal bar itself, because the entry only fills at the next open. So the tracker is already 0 again when the position exists, the target / trailing block
(which requires the tracker to be long / short) never runs, no exit order is ever issued, and the position is only ever reversed by the next opposite confluence signal. The block is translated as written.
Deviations from the original: none.
Not carried over: nothing (no display code in the source).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, ta


class EmaFibConfluence(Script):
    TITLE = "EMA & Fib Confluence with 3 Targets + Trailing v6"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "diZ8Oes6", "author": "alanshospitality", "licence": "not stated",
              "url": "https://www.tradingview.com/script/diZ8Oes6-EMA-Fib-Confluence-with-3-Targets-Trailing-v6"}

    def init(self):
        i = self.input
        g = "EMA Trend Settings"
        self.fast_ema_len = i.int(9, "Fast EMA Length", group=g)
        self.slow_ema_len = i.int(21, "Slow EMA Length", group=g)
        g = "Fibonacci Levels"
        self.fib_lookback = i.int(50, "Fibonacci Lookback Period", group=g)
        self.fib_level_entry = i.float(0.618, "Fib Entry Target Ratio", group=g)
        g = "Take Profit Settings"
        self.tp1_pct = i.float(1.0, "Target 1 (%)", group=g) / 100
        self.tp2_pct = i.float(2.0, "Target 2 (%)", group=g) / 100
        self.tp3_pct = i.float(3.5, "Target 3 (%)", group=g) / 100
        g = "Position Scaling"
        self.tp1_qty = i.float(33.0, "Target 1 Close Qty (%)", group=g)
        self.tp2_qty = i.float(33.0, "Target 2 Close Qty (%)", group=g)
        self.tp3_qty = i.float(34.0, "Target 3 Close Qty (%)", group=g)
        self.trail_pct = i.float(1.5, "Trailing Distance (%)", group="Trailing Stop Settings") / 100
        self.entry_price = NA
        self.t1_price = NA
        self.t2_price = NA
        self.t3_price = NA
        self.trailing_stop = NA
        self.active_position_type = 0

    def on_bar(self):
        st = self.strategy
        close = self.close
        fast_ema = ta.ema(close, self.fast_ema_len)
        slow_ema = ta.ema(close, self.slow_ema_len)
        highest_high = ta.highest(self.high, self.fib_lookback)
        lowest_low = ta.lowest(self.low, self.fib_lookback)
        price_range = highest_high - lowest_low
        fib_long_level = highest_high - (price_range * self.fib_level_entry)
        fib_short_level = lowest_low + (price_range * self.fib_level_entry)
        cross_over_long = ta.crossover(close, fib_long_level)
        cross_under_short = ta.crossunder(close, fib_short_level)
        cross_under_ema = ta.crossunder(fast_ema, slow_ema)
        cross_over_ema = ta.crossover(fast_ema, slow_ema)
        buy_confluence = (fast_ema > slow_ema) and cross_over_long
        sell_confluence = (fast_ema < slow_ema) and cross_under_short
        if buy_confluence and self.active_position_type == 0:
            self.entry_price = float(close)
            self.t1_price = close * (1 + self.tp1_pct)
            self.t2_price = close * (1 + self.tp2_pct)
            self.t3_price = close * (1 + self.tp3_pct)
            self.trailing_stop = close * (1 - self.trail_pct)
            self.active_position_type = 1
            st.entry("Long", st.long)
        if sell_confluence and self.active_position_type == 0:
            self.entry_price = float(close)
            self.t1_price = close * (1 - self.tp1_pct)
            self.t2_price = close * (1 - self.tp2_pct)
            self.t3_price = close * (1 - self.tp3_pct)
            self.trailing_stop = close * (1 + self.trail_pct)
            self.active_position_type = -1
            st.entry("Short", st.short)
        if st.position_size > 0 and self.active_position_type == 1:
            st.exit("T1 Long", from_entry="Long", qty_percent=self.tp1_qty, limit=self.t1_price)
            st.exit("T2 Long", from_entry="Long", qty_percent=self.tp2_qty, limit=self.t2_price)
            st.exit("T3 Long", from_entry="Long", qty_percent=self.tp3_qty, limit=self.t3_price)
            if close * (1 - self.trail_pct) > self.trailing_stop:
                self.trailing_stop = close * (1 - self.trail_pct)
            if close <= self.trailing_stop or cross_under_ema:
                st.close("Long", comment="Trailing Stop or Reverse Cross")
                self.active_position_type = 0
        if st.position_size < 0 and self.active_position_type == -1:
            st.exit("T1 Short", from_entry="Short", qty_percent=self.tp1_qty, limit=self.t1_price)
            st.exit("T2 Short", from_entry="Short", qty_percent=self.tp2_qty, limit=self.t2_price)
            st.exit("T3 Short", from_entry="Short", qty_percent=self.tp3_qty, limit=self.t3_price)
            if close * (1 + self.trail_pct) < self.trailing_stop:
                self.trailing_stop = close * (1 + self.trail_pct)
            if close >= self.trailing_stop or cross_over_ema:
                st.close("Short", comment="Trailing Stop or Reverse Cross")
                self.active_position_type = 0
        if st.position_size == 0:
            self.active_position_type = 0
