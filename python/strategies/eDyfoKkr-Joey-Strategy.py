"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Joey Strategy
Author       : Geckin
Source URL   : https://www.tradingview.com/script/eDyfoKkr-Joey-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Long when %K (stochastic 14 smoothed by SMA 3) crosses over %D (SMA 3 of %K) below 30 and flat. On the
first bar on which the position is open at the close, the entry price and ATR are frozen into var levels (entry +/- 1.5 ATR) and a
bracket exit is issued from then on, so it first works on the bar after the fill.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


class JoeyStrategy(Script):
    TITLE = "Joey Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0)
    SOURCE = {"id": "eDyfoKkr", "author": "Geckin", "licence": "not stated",
              "url": "https://www.tradingview.com/script/eDyfoKkr-Joey-Strategy"}

    def init(self):
        self.length = self.input.int(14, "Stochastic Length", minval=1)
        self.over_sold = self.input.int(30, "Oversold")
        self.smooth_k = self.input.int(3, "Smooth K", minval=1)
        self.smooth_d = self.input.int(3, "Smooth D", minval=1)
        self.atr_length = self.input.int(14, "ATR Length", minval=1)
        self.atr_multiplier = self.input.float(1.5, "ATR Take Profit / Stop Loss Multiplier", minval=0.1, step=0.1)
        self.trade_entry_price = NA
        self.trade_atr_at_entry = NA
        self.take_profit_price = NA
        self.stop_loss_price = NA

    def on_bar(self):
        k = ta.sma(ta.stoch(self.close, self.high, self.low, self.length), self.smooth_k)
        d = ta.sma(k, self.smooth_d)
        long_signal = ta.crossover(k, d) and k < self.over_sold
        atr = ta.atr(self.atr_length)
        st = self.strategy
        prev_pos = self.H("pos")[1]                              # strategy.position_size[1]
        if long_signal and st.position_size == 0:
            st.entry("Enter", st.long, comment="Enter")
        new_long_position = st.position_size > 0 and prev_pos == 0
        if new_long_position:
            self.trade_entry_price = st.position_avg_price
            self.trade_atr_at_entry = atr
            self.take_profit_price = self.trade_entry_price + self.trade_atr_at_entry * self.atr_multiplier
            self.stop_loss_price = self.trade_entry_price - self.trade_atr_at_entry * self.atr_multiplier
        if st.position_size == 0:
            self.trade_entry_price = NA
            self.trade_atr_at_entry = NA
            self.take_profit_price = NA
            self.stop_loss_price = NA
        if st.position_size > 0 and not na(self.take_profit_price) and not na(self.stop_loss_price):
            st.exit("Exit", from_entry="Enter", qty_percent=100, limit=self.take_profit_price,
                    stop=self.stop_loss_price, comment="Exit")
        self.H("pos").set(st.position_size)
