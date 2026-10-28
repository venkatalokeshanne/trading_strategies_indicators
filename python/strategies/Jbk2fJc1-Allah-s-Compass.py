"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Allah's Compass
Author       : mpio222
Source URL   : https://www.tradingview.com/script/Jbk2fJc1-Allah-s-Compass
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. BB%B (20, 2) crossing up through 0 enters long when flat with a percent stop; a bullish
divergence (lower close, higher BB%B below 0.2 versus 10 bars ago) while long updates the stop, and its "Long_Add" entry is
ignored because pyramiding is 1; the stop and the BB%B >= 1 exit close everything at the next open.

Deviations from the original: none.
Not carried over: the BB% pane styling, zones and shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, div, na, pmath, ta


class AllahsCompass(Script):
    TITLE = "Allah's Compass"
    PINE_VERSION = 5
    OVERLAY = False
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "Jbk2fJc1", "author": "mpio222", "licence": "not stated",
              "url": "https://www.tradingview.com/script/Jbk2fJc1-Allah-s-Compass"}

    def init(self):
        self.bb_length = self.input.int(20, "BB Length")
        self.bb_mult = self.input.float(2.0, "BB StdDev Multiplier")
        self.stop_loss_pct = self.input.float(100.0, "Stop Loss %", step=0.1)
        self.div_lookback = self.input.int(10, "Divergence Lookback Bars")
        self.stop_price = NA

    def on_bar(self):
        basis = ta.sma(self.close, self.bb_length)
        dev = self.bb_mult * ta.stdev(self.close, self.bb_length)
        upper = basis + dev
        lower = basis - dev
        bb_pct = S(div(self.close - lower, upper - lower))
        c = S(self.close)
        cross_into_green = ta.crossover(bb_pct[0], 0.0)
        prev_price_low = c[self.div_lookback]
        prev_bb_pct_low = bb_pct[self.div_lookback]
        bullish_div = S((self.close < prev_price_low) and (bb_pct[0] > prev_bb_pct_low) and (bb_pct[0] < 0.2))
        st = self.strategy
        div_add_on = bullish_div[0] and (not bullish_div[1]) and st.position_size > 0
        exit_signal = bb_pct[0] >= 1.0
        if cross_into_green and st.position_size == 0:
            st.entry("Long", st.long)
            self.stop_price = self.close * (1 - self.stop_loss_pct / 100)
        if div_add_on:
            st.entry("Long_Add", st.long, qty=2)
            self.stop_price = pmath.min(self.stop_price, self.close * (1 - self.stop_loss_pct / 100))
        if st.position_size > 0 and self.close <= self.stop_price:
            st.close_all(comment="Stop Loss")
            self.stop_price = NA
        if exit_signal and st.position_size > 0:
            st.close_all(comment="BB% Top Exit")
            self.stop_price = NA
        self.plot(bb_pct[0], "BB%", color=color.green)
