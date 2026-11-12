"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : MNQ Liquidity Sweep Strategy ( KUSH )
Author       : guptakush961
Source URL   : https://www.tradingview.com/script/cnydr3fS-MNQ-Liquidity-Sweep-Strategy-KUSH
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

Stop-and-reverse: strategy.entry in either direction reverses an open position
(pinelib's broker does this exactly as Pine does). `when =` becomes an if.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, ta


class MnqLiquiditySweep(Script):
    TITLE = "MNQ Liquidity Sweep Strategy"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "cnydr3fS", "author": "guptakush961", "licence": "not stated",
              "url": "https://www.tradingview.com/script/cnydr3fS-MNQ-Liquidity-Sweep-Strategy-KUSH"}

    def init(self):
        self.lookback = 20                                   # hard-coded in the Pine source

    def on_bar(self):
        highest_high = S(ta.highest(self.high, self.lookback))
        lowest_low = S(ta.lowest(self.low, self.lookback))
        short_condition = self.high > highest_high[1] and self.close < self.low[1]
        long_condition = self.low < lowest_low[1] and self.close > self.high[1]
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long)
        if short_condition:
            st.entry("Short", st.short)
