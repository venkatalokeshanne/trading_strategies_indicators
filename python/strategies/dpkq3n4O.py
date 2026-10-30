"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : LinReg Scale-In Strategy
Author       : p_zerbst
Source URL   : https://www.tradingview.com/script/dpkq3n4O
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. ta.correlation(close, bar_index, length) is the Pearson correlation of
price with the bar number (the "linear regression coefficient"). pyramiding=3 lets the three
level entries stack; close_all exits them all when the coefficient falls back under 0.25.

Deviations from the original: none.
Not carried over: the hline() reference lines (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class LinRegScaleIn(Script):
    TITLE = "LinReg Scale-In Strategy"
    PINE_VERSION = 5
    OVERLAY = False
    STRATEGY = dict(pyramiding=3, initial_capital=100000, default_qty_type="fixed", default_qty_value=1)
    SOURCE = {"id": "dpkq3n4O", "author": "p_zerbst", "licence": "not stated",
              "url": "https://www.tradingview.com/script/dpkq3n4O"}

    def init(self):
        self.length = self.input.int(20, "Lookback Period", minval=5)

    def on_bar(self):
        coeff = ta.correlation(self.close, self.bar_index, self.length)
        self.plot(coeff, color=color.blue, title="LinReg Coefficient", linewidth=2)
        cross_up_25 = ta.crossover(coeff, 0.25)
        cross_up_50 = ta.crossover(coeff, 0.50)
        cross_up_75 = ta.crossover(coeff, 0.75)
        cross_down_25 = ta.crossunder(coeff, 0.25)
        st = self.strategy
        if cross_up_25:
            st.entry("Long @ 0.25", st.long)
        if cross_up_50:
            st.entry("Long @ 0.50", st.long)
        if cross_up_75:
            st.entry("Long @ 0.75", st.long)
        if cross_down_25:
            st.close_all(comment="Exit < 0.25")
