"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA 9,20 with Support and Resistance Breakout v5
Author       : ankurb171991
Source URL   : https://www.tradingview.com/script/5EGVP61U-EMA-9-20-with-Support-and-Resistance-Breakout
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation, process_orders_on_close = true. EMA9 crossing over (under) EMA20 with the close beyond EMA9 and a
candle body of at least 30 % of its range enters long (short) at that bar's close when flat. strategy.position_size inside the
script is the position BEFORE the bar's close fills, so the 12 % target / 6 % stop around the average price is first issued on the
bar after the fill and works from the one after.

Deviations from the original: none.
Not carried over: the EMA plots, pivot lines and signal shapes (the pivot calls feed no order).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, ta


class EmaSrBreakoutV5(Script):
    TITLE = "EMA 9,20 with Support and Resistance Breakout v5"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10, process_orders_on_close=True)
    SOURCE = {"id": "5EGVP61U", "author": "ankurb171991", "licence": "not stated",
              "url": "https://www.tradingview.com/script/5EGVP61U-EMA-9-20-with-Support-and-Resistance-Breakout"}

    def init(self):
        self.ema9_len = self.input.int(9, "EMA Fast")
        self.ema20_len = self.input.int(20, "EMA Slow")
        self.sr_lookback = self.input.int(20, "S/R Lookback Bars")
        self.target_pct = self.input.float(12.0, "Target %", step=0.5) / 100
        self.sl_pct = self.input.float(6.0, "Stop Loss %", step=0.5) / 100

    def on_bar(self):
        ema9 = ta.ema(self.close, self.ema9_len)
        ema20 = ta.ema(self.close, self.ema20_len)
        candle_range = self.high - self.low
        candle_body = abs(self.close - self.open)
        strong_candle = candle_range > 0 and div(candle_body, candle_range) >= 0.3
        ema_cross_up = ta.crossover(ema9, ema20)
        ema_cross_down = ta.crossunder(ema9, ema20)
        buy_condition = ema_cross_up and self.close > ema9 and strong_candle
        sell_condition = ema_cross_down and self.close < ema9 and strong_candle
        st = self.strategy
        flat = st.position_size == 0
        in_long = st.position_size > 0
        in_short = st.position_size < 0
        if buy_condition and flat:
            st.entry("Long", st.long)
        if sell_condition and flat:
            st.entry("Short", st.short)
        if in_long:
            st.exit("Long Exit", "Long", limit=st.position_avg_price * (1 + self.target_pct),
                    stop=st.position_avg_price * (1 - self.sl_pct), comment_profit="TP +12%", comment_loss="SL -6%")
        if in_short:
            st.exit("Short Exit", "Short", limit=st.position_avg_price * (1 - self.target_pct),
                    stop=st.position_avg_price * (1 + self.sl_pct), comment_profit="TP +12%", comment_loss="SL -6%")
        self.plot(ema9, "EMA 9", color=color.orange, linewidth=2)
        self.plot(ema20, "EMA 20", color=color.blue, linewidth=2)
