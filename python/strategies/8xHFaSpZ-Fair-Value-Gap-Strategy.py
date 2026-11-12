"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Fair Value Gap Strategy
Author       : SadTrader9
Source URL   : https://www.tradingview.com/script/8xHFaSpZ-Fair-Value-Gap-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A bullish gap (high two bars ago below this low) buys, a bearish gap
sells short; opposite signals reverse. Pine default sizing (1 contract). margin_long/short = 100.

Deviations from the original: none.
Not carried over: the FVG rectangles (box.new, written but never read back) and the plotshape labels.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script


class FairValueGap(Script):
    TITLE = "Fair Value Gap Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(margin_long=100, margin_short=100)
    SOURCE = {"id": "8xHFaSpZ", "author": "SadTrader9", "licence": "not stated",
              "url": "https://www.tradingview.com/script/8xHFaSpZ-Fair-Value-Gap-Strategy"}

    def on_bar(self):
        bullish_fvg = self.high[2] < self.low
        bearish_fvg = self.low[2] > self.high
        self.plotshape(bullish_fvg, title="Bullish FVG")
        self.plotshape(bearish_fvg, title="Bearish FVG")
        st = self.strategy
        if bullish_fvg:
            st.entry("Long", st.long)
        if bearish_fvg:
            st.entry("Short", st.short)
