"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 55/20 Wilder's MACD Trend Armbrust Capital
Author       : ArmbrustCapital
Source URL   : https://www.tradingview.com/script/AR7LCcVC-55-20-Wilder-s-MACD-Trend-Armbrust-Capital
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

`signalLength` is declared but unused in the Pine source; kept as an input.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class WildersMacdTrend(Script):
    TITLE = "55/20 Wilder's MACD Trend"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "AR7LCcVC", "author": "ArmbrustCapital", "licence": "not stated",
              "url": "https://www.tradingview.com/script/AR7LCcVC-55-20-Wilder-s-MACD-Trend-Armbrust-Capital"}

    def init(self):
        self.fast_length = self.input(20)
        self.slow_length = self.input(55)
        self.signal_length = self.input(10, title="Signal Length")

    def on_bar(self):
        price = self.close[0]
        mafast = ta.rma(price, self.fast_length)
        maslow = ta.rma(price, self.slow_length)
        st = self.strategy
        if ta.crossover(mafast, maslow):
            st.entry("MA2CrossLE", st.long, comment="MA2CrossLE")
        if ta.crossunder(mafast, maslow):
            st.entry("MA2CrossSE", st.short, comment="MA2CrossSE")
