"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Turtle Trading Strategy with ATR Stop + Pyramiding
Author       : Snorkle1990
Source URL   : https://www.tradingview.com/script/HYco13Su-Turtle-Trading-Strategy-with-ATR-Stop-Pyramiding
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). A close above the previous 20 bars' highest high (with the SMA200 trend filter) buys. As in the original,
the "if position_size == 0" reset block runs after the entry on the entry bar itself (the position is still flat at script time), so the last entry price is cleared and
the pyramiding condition can never be met: the strategy effectively holds one lot at a time. An ATR stop that ratchets up and the 10-bar channel exit (edge-triggered)
close the position.

Deviations from the original: none.
Not carried over: the line plots, BUY / SELL labels, bar colouring and alerts (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, pmath, ta


class TurtlePyramid(Script):
    TITLE = "Turtle Trading Strategy with ATR Stop + Pyramiding"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, pyramiding=4, process_orders_on_close=True)
    SOURCE = {"id": "HYco13Su", "author": "Snorkle1990", "licence": "not stated",
              "url": "https://www.tradingview.com/script/HYco13Su-Turtle-Trading-Strategy-with-ATR-Stop-Pyramiding"}

    def init(self):
        self.entry_length = self.input.int(20, "Entry Breakout Length", minval=1)
        self.exit_length = self.input.int(10, "Exit Breakout Length", minval=1)
        self.trend_ma_length = self.input.int(200, "Trend MA Length", minval=1)
        self.use_trend_filter = self.input.bool(True, "Use Trend Filter")
        self.atr_length = self.input.int(20, "ATR Length", minval=1)
        self.atr_stop_multiple = self.input.float(2.0, "ATR Stop Multiple", minval=0.1, step=0.1)
        self.risk_pct = self.input.float(25, "Position Size % Per Entry", minval=1, maxval=100)
        self.max_pyramid = self.input.int(4, "Maximum Pyramid Entries", minval=1, maxval=10)
        self.last_entry_price = NA
        self.pyramid_count = 0
        self.atr_stop = NA

    def on_bar(self):
        c = self.close
        trend_ma = ta.sma(c, self.trend_ma_length)
        entry_high = ta.highest(self.high[1], self.entry_length)
        exit_low = ta.lowest(self.low[1], self.exit_length)
        atr_value = ta.atr(self.atr_length)
        trend_filter = c > trend_ma
        raw_buy = c > entry_high and ((not self.use_trend_filter) or trend_filter)
        st = self.strategy
        can_add = st.position_size == 0 or (st.position_size > 0 and self.pyramid_count < self.max_pyramid
                                            and c >= self.last_entry_price + (0.5 * atr_value))
        buy_signal = raw_buy and can_add
        position_value = st.equity * (self.risk_pct / 100.0)
        qty = div(position_value, c)
        if buy_signal:
            self.pyramid_count += 1
            self.last_entry_price = float(c)
            st.entry("Long_" + str(self.pyramid_count), st.long, qty=qty)
            if st.position_size == 0:
                self.atr_stop = c - atr_value * self.atr_stop_multiple
        if st.position_size == 0:
            self.pyramid_count = 0
            self.last_entry_price = NA
            self.atr_stop = NA
        if st.position_size > 0:
            new_stop = c - atr_value * self.atr_stop_multiple
            self.atr_stop = new_stop if na(self.atr_stop) else pmath.max(self.atr_stop, new_stop)
        exit_signal_channel = st.position_size > 0 and c < exit_low
        exit_signal_atr = st.position_size > 0 and c < self.atr_stop
        raw_sell = exit_signal_channel or exit_signal_atr
        prev_raw_sell = self.H("raw_sell")[1]
        self.H("raw_sell").set(raw_sell)
        sell_signal = raw_sell and not prev_raw_sell
        if st.position_size > 0 and not na(self.atr_stop):
            st.exit("ATR Stop", stop=self.atr_stop)
        if sell_signal:
            st.close_all("Exit All")
        self.plot(trend_ma, "Trend MA", color=color.blue, linewidth=2)
        self.plot(entry_high, "Entry Breakout", color=color.green, linewidth=2)
        self.plot(exit_low, "Exit Breakdown", color=color.red, linewidth=2)
