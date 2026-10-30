"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : My strategy 9
Author       : klowdcossey99
Source URL   : https://www.tradingview.com/script/KPoMQJ46-My-strategy-9
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. SMA(14) / SMA(28) cross reverses between long and short (default 1 contract, no brackets).

Deviations from the original: none in trading logic.
Not carried over: f_getHighLow (never called) and the plots of the daily / 60 / 30 / 15-minute highs and lows
(cosmetic request.security calls that do not feed any order).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class MyStrategy9(Script):
    TITLE = "My strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "KPoMQJ46", "author": "klowdcossey99", "licence": "not stated",
              "url": "https://www.tradingview.com/script/KPoMQJ46-My-strategy-9"}

    def on_bar(self):
        st = self.strategy
        fast = ta.sma(self.close, 14)
        slow = ta.sma(self.close, 28)
        if ta.crossover(fast, slow):
            st.entry("My Long Entry Id", st.long)
        if ta.crossunder(ta.sma(self.close, 14), ta.sma(self.close, 28)):
            st.entry("My Short Entry Id", st.short)
